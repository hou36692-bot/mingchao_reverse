"""Run only through UE-MCP. Author the Eye graph from the tracked semantic sources.

The existing character is not rebound by this script. Rebuilding an asset created
by this script requires the explicit rebuild_owned flag. Calibration is read from
EyeCalibration.json; source capture files and learning copies are not runtime inputs.
"""
import json
import re
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
assert ROOT.as_posix().rstrip('/').lower() == 'd:/ue_project/mingchao_reverse'
BASE = '/Game/MingchaoReverse/Materials/SemanticRebuild'
lib = unreal.MaterialEditingLibrary
assets = unreal.EditorAssetLibrary
path = BASE + '/M_SR_Eye'
material = unreal.load_asset(path)
if material:
    assert globals().get('rebuild_owned', False), 'Existing material requires explicit rebuild_owned'
    for expression in list(lib.get_material_expressions(material)):
        lib.delete_material_expression(material,expression)
else:
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_SR_Eye', BASE, unreal.Material, unreal.MaterialFactoryNew())
material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)
material.set_editor_property('used_with_skeletal_mesh', True)
material.set_editor_property('two_sided', False)
calibration = json.loads((ROOT / 'Shaders/SemanticRebuild/EyeCalibration.json').read_text())
eye_source = (ROOT / 'Shaders/SemanticRebuild/Eye.ush').read_text()
light_source = (ROOT / 'Shaders/SemanticRebuild/CharacterLighting.ush').read_text()
nodes = {}
group_rows = {}
stage = globals().get('eye_stage', 3)

def node(kind, x=0, y=0):
    return lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind), x, y)

def wire(source, target, pin):
    assert lib.connect_material_expressions(source[0], source[1], target, pin), (source, target, pin)

def parameter(name):
    if name in nodes:
        return nodes[name]
    data = calibration[name]
    value = data['value']
    group = data['group']
    group_index = int(group[:2]) - 1
    row = group_rows.get(group, 0)
    group_rows[group] = row + 1
    x, y = -3200 + group_index * 400, 1000 + row * 190
    expression = node('VectorParameter' if isinstance(value, list) else 'ScalarParameter', x, y)
    expression.set_editor_property('parameter_name', name)
    expression.set_editor_property('group', group)
    expression.set_editor_property('sort_priority', row)
    expression.set_editor_property('desc', data['meaning'] + '; ' + data['source'])
    if isinstance(value, list):
        expression.set_editor_property('default_value', unreal.LinearColor(*(value + [0] * (4-len(value)))))
        if len(value) == 4:
            append = node('AppendVector', x + 200, y)
            wire((expression, 'RGB'), append, 'A')
            wire((expression, 'A'), append, 'B')
            result = (append, '')
        elif len(value) == 2:
            mask = node('ComponentMask', x + 200, y)
            for key, enabled in zip(('r','g','b','a'), (True,True,False,False)):
                mask.set_editor_property(key, enabled)
            wire((expression, 'RGB'), mask, '')
            result = (mask, '')
        else:
            result = (expression, 'RGB')
    else:
        expression.set_editor_property('default_value', value)
        if name.endswith('Width') or name in ('SharedScale','ControlEdgeWidth'):
            expression.set_editor_property('slider_min', 0.000001)
        result = (expression, '')
    nodes[name] = result
    return result

def custom(name, code, inputs, outputs=None, size=3, x=0, y=0, include='Eye.ush'):
    expression = node('Custom', x, y)
    expression.set_editor_property('description', name)
    expression.set_editor_property('code', code)
    expression.set_editor_property('include_file_paths', ['/MingchaoSemantic/' + include])
    expression.set_editor_property('output_type', getattr(unreal.CustomMaterialOutputType, 'CMOT_FLOAT' + str(size)))
    pins = []
    for key in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', key)
        pins.append(pin)
    expression.set_editor_property('inputs', pins)
    extra = []
    for key, count in (outputs or {}).items():
        output = unreal.CustomOutput()
        output.set_editor_property('output_name', key)
        output.set_editor_property('output_type', getattr(unreal.CustomMaterialOutputType, 'CMOT_FLOAT' + str(count)))
        extra.append(output)
    expression.set_editor_property('additional_outputs', extra)
    # UE exposes some reserved names through display aliases (MipBias -> Bias).
    input_names = lib.get_material_expression_input_names(expression)
    assert len(input_names) == len(inputs)
    for source, input_name in zip(inputs.values(), input_names):
        wire(source, expression, str(input_name))
    return expression

def settings(type_name, source):
    body = re.search(r'struct ' + type_name + r'\s*\{(.*?)\};', source, re.S).group(1)
    names = re.findall(r'float[234]?\s+(\w+)\s*;', body)
    return type_name + ' Settings;\n' + ''.join('Settings.' + n + '=' + n + ';\n' for n in names), {n: parameter(n) for n in names}

def texture(name, asset_path, srgb):
    tex = unreal.load_asset(asset_path)
    assert tex and tex.get_editor_property('srgb') == srgb, 'Texture color-space contract: ' + asset_path
    if name in ('LayerMap','ControlMap','ColorMap','DirectionMap'):
        # Preserve shared U2 textures. These copies use the same intrinsic source
        # pixels, with the captured resource's sampler and mip-count contract.
        target_path = '/Game/MingchaoReverse/Textures/SemanticRebuild/' + asset_path.rsplit('/',1)[1] + '_SR'
        copy = unreal.load_asset(target_path)
        if not copy:
            copy = assets.duplicate_asset(asset_path, target_path)
        tex = copy
        address = unreal.TextureAddress.TA_WRAP if name == 'ColorMap' else unreal.TextureAddress.TA_CLAMP
        tex.set_editor_property('address_x', address)
        tex.set_editor_property('address_y', address)
        tex.set_editor_property('filter', unreal.TextureFilter.TF_TRILINEAR if name == 'DirectionMap' else unreal.TextureFilter.TF_BILINEAR)
        if name in ('LayerMap','DirectionMap'):
            tex.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        assets.save_loaded_asset(tex)
    expression = node('TextureObjectParameter', -1800, -600 + 180 * len(textures))
    expression.set_editor_property('parameter_name', name)
    expression.set_editor_property('texture', tex)
    expression.set_editor_property('group', '00 Source textures')
    expression.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if srgb else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    textures[name] = (expression, '')
    return textures[name]

textures = {}
uv = node('TextureCoordinate', -2400, -800)
uv.set_editor_property('coordinate_index', 0)
uv1 = node('TextureCoordinate', -2400, -650)
uv1.set_editor_property('coordinate_index', 1)
vertex = node('VertexColor', -2400, -450)
clock = node('Time', -2400, -200)
clock_input = custom('Clock: frozen source time plus optional animation', 'return TimeSeconds + Elapsed * AnimationRate;', {'TimeSeconds':parameter('TimeSeconds'), 'Elapsed':(clock,''), 'AnimationRate':parameter('AnimationRate')}, size=1, x=-2000, y=-200)
body, inputs = settings('SR_EyeCoordinates', eye_source)
inputs.update(UV=(uv,''), VertexGreen=(vertex,'G'), Clock=(clock_input,''))
coordinates = custom('01 Layer coordinates | E548 18-58', body + 'return SR_EyeLayerUV(UV,VertexGreen,Clock,Settings,Pulse,Jitter);', inputs, {'Pulse':1,'Jitter':1}, size=2, x=-1400, y=-500)
preview = custom('UV diagnostic', 'return float3(frac(UV),0);', {'UV':(coordinates,'')}, x=-900, y=-500)
if stage >= 2:
    texture('LayerMap', '/Game/MingchaoReverse/Textures/Character/T_EyesSecondHeightLight04_EG', False)
    texture('ControlMap', '/Game/MingchaoReverse/Textures/Character/T_HDMF_EM', True)
    texture('ColorMap', '/Game/MingchaoReverse/Textures/Character/T_R2T1KatixiyaMd10011Eye_D', True)
    view = node('CameraVectorWS', -2400, 0)
    tangent_view = node('Transform', -2000, 0)
    tangent_view.set_editor_property('transform_source_type', unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
    tangent_view.set_editor_property('transform_type', unreal.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    wire((view,''), tangent_view, '')
    body, inputs = settings('SR_EyeSurfaceSettings', eye_source)
    inputs.update(textures)
    inputs.update(UV=(uv,''), LayerUV=(coordinates,''), VertexGreen=(vertex,'G'), VertexEmission=parameter('VertexEmission'), ViewTangent=(tangent_view,''), Pulse=(coordinates,'Pulse'), Jitter=(coordinates,'Jitter'))
    surface = custom('02 Surface, search and emission | E548 61-246', body + 'return SR_EyeSurface(LayerMap,LayerMapSampler,ControlMap,ControlMapSampler,ColorMap,ColorMapSampler,UV,LayerUV,VertexGreen,VertexEmission,ViewTangent,Pulse,Jitter,Settings,Emission,SearchUV,AlphaControl,RingRadius);', inputs, {'Emission':3,'SearchUV':2,'AlphaControl':1,'RingRadius':1}, x=-600, y=-350)
    preview = surface
if stage >= 3:
    texture('DirectionMap', '/Game/MingchaoReverse/Textures/Character/T_FemaleMFace_SDF', False)
    collection = unreal.load_asset('/Game/MingchaoReverse/Materials/U2/MPC_ReferenceScene')
    def scene_value(name, x, y):
        expression = node('CollectionParameter', x, y)
        expression.set_editor_property('collection', collection)
        expression.set_editor_property('parameter_name', name)
        return (expression,'')
    mask_inputs = {'DirectionMap':textures['DirectionMap'], 'UV1':(uv1,''), 'AlphaControl':(surface,'AlphaControl')}
    for name in ('StyleDirection','FlatDirection','FlattenEnabled','FlattenWeight','MirrorMode','MirrorBlend','UseAlternateUV','AlternateSide','AlphaCap','AlphaSuppression','ThresholdCenter','ThresholdWidth'):
        mask_inputs[name] = parameter(name)
    mask_inputs.update(HeadForward=scene_value('HeadForward',-1000,-900), HeadRight=scene_value('HeadRight',-1000,-750))
    light_mask = custom('03 Direction and light mask | E548 247-359', 'return SR_EyeLightMask(DirectionMap,DirectionMapSampler,UV1,AlphaControl,StyleDirection,FlatDirection,FlattenEnabled,FlattenWeight,HeadForward.xyz,HeadRight.xyz,MirrorMode,MirrorBlend,UseAlternateUV,AlternateSide,AlphaCap,AlphaSuppression,ThresholdCenter,ThresholdWidth,DirectionWeight);', mask_inputs, {'DirectionWeight':1}, size=1, x=100, y=-600)
    world_position = node('WorldPosition', -1000,-1100)
    depth = node('PixelDepth', -1000,-1300)
    texture('BangsDepth', '/Game/MingchaoReverse/Materials/U52/Runtime/RT_U52_BangsDepth', False)
    auxiliary_inputs = {'BangsDepth':textures['BangsDepth'], 'WorldPosition':(world_position,''), 'CaptureOrigin':scene_value('ReferenceCamera',-800,-1100), 'SurfaceMask':(light_mask,'')}
    for name in ('CaptureForward','CaptureRight','CaptureUp','CaptureTanHalfFov','BangsShadowEnabled'):
        auxiliary_inputs[name] = parameter(name)
    auxiliary = custom('04 Existing U52 producer adapter', 'return SR_ApplyBangsShadow(BangsDepth,WorldPosition,CaptureOrigin.xyz,CaptureForward,CaptureRight,CaptureUp,CaptureTanHalfFov,BangsShadowEnabled,SurfaceMask,Occluded);', auxiliary_inputs, {'Occluded':1}, size=1, x=750,y=-600, include='CharacterLighting.ush')
    body, inputs = settings('SR_CharacterLightSettings', light_source)
    inputs.update(Base=(surface,''), SecondaryTint=parameter('SecondaryTint'), LightMask=(auxiliary,''), ExtraControl=parameter('ExtraControl'), Visibility=parameter('Visibility'), ViewDepthCm=(depth,''))
    lighting = custom('05 Character lighting | E1401 246-318', body + 'return SR_EvaluateCharacterLighting(Base,SecondaryTint,LightMask,ExtraControl,Visibility,ViewDepthCm,Settings,ShadowContribution,SecondaryContribution,BrightWeight);', inputs, {'ShadowContribution':3,'SecondaryContribution':3,'BrightWeight':1}, x=1400,y=-350,include='CharacterLighting.ush')
    diagnostics = {'Mode':parameter('DebugMode'),'Lighting':(lighting,''),'Base':(surface,''),'Emission':(surface,'Emission'),'UV':(coordinates,''),'SearchUV':(surface,'SearchUV'),'Alpha':(surface,'AlphaControl'),'Mask':(auxiliary,''),'Direction':(light_mask,'DirectionWeight'),'Shadow':(lighting,'ShadowContribution'),'Secondary':(lighting,'SecondaryContribution'),'Bright':(lighting,'BrightWeight'),'Occluded':(auxiliary,'Occluded')}
    preview = custom('06 Output and diagnostics', 'if(Mode<0.5)return Lighting+Emission; if(Mode<1.5)return float3(frac(UV),0); if(Mode<2.5)return Base; if(Mode<3.5)return Emission; if(Mode<4.5)return float3(SearchUV,0); if(Mode<5.5)return Alpha.xxx; if(Mode<6.5)return Mask.xxx; if(Mode<7.5)return Direction.xxx; if(Mode<8.5)return Shadow; if(Mode<9.5)return Secondary; if(Mode<10.5)return Bright.xxx; return Occluded.xxx;', diagnostics, x=2000,y=-350)
assert lib.connect_material_property(preview, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
lib.recompile_material(material)
instance = unreal.load_asset(BASE + '/Instances/MI_SR_Eye')
if not instance:
    instance = unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_SR_Eye', BASE + '/Instances', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
lib.set_material_instance_parent(instance, material)
assets.save_loaded_asset(material)
assets.save_loaded_asset(instance)
print(json.dumps({'stage':stage,'material':material.get_path_name(),'instance':instance.get_path_name(),'parameters':list(nodes),'component_binding_changed':False}))
