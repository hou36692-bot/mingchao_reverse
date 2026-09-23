"""Author R5 producers through UE-MCP. Scene binding is a separate operation."""
import json
from pathlib import Path
import unreal

BASE='/Game/MingchaoReverse/Materials/SemanticRebuild'
ROOT=Path('D:/UE_Project/mingchao_reverse')
EVIDENCE=Path('D:/HOU/mingchao_reverse/assets/ue_u52')
lib=unreal.MaterialEditingLibrary
assets=unreal.EditorAssetLibrary

def context():
    assert unreal.Paths.get_project_file_path().replace('\\','/').lower().endswith('/mingchao_reverse/mingchao_reverse.uproject')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name()=='/Game/Maps/L_Katixiya_Reference.L_Katixiya_Reference'
    actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
    return world,actors

def create(name):
    m=unreal.load_asset(BASE+'/M_SR_'+name)
    if m:
        # Iterate a snapshot: deletion mutates the stored expression collection.
        for n in list(lib.get_material_expressions(m)):lib.delete_material_expression(m,n)
    else:m=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_SR_'+name,BASE,unreal.Material,unreal.MaterialFactoryNew())
    m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('used_with_skeletal_mesh',True)
    m.set_editor_property('two_sided',False)
    return m

def node(m,kind):return lib.create_material_expression(m,getattr(unreal,'MaterialExpression'+kind))
def wire(pair,n,pin):assert lib.connect_material_expressions(pair[0],pair[1],n,pin)
def param(m,key,value,group='01 Controls'):
    n=node(m,'VectorParameter' if isinstance(value,list) else 'ScalarParameter')
    n.set_editor_property('parameter_name',key);n.set_editor_property('group',group)
    if isinstance(value,list):
        n.set_editor_property('default_value',unreal.LinearColor(*(value+[0]*(4-len(value)))))
        if len(value)==2:
            mask=node(m,'ComponentMask')
            for k,v in zip('rgba',(True,True,False,False)):mask.set_editor_property(k,v)
            wire((n,'RGB'),mask,'');return (mask,'')
        return (n,'RGB')
    n.set_editor_property('default_value',value);return (n,'')

def custom(m,label,code,inputs,size=3,include='Auxiliary.ush'):
    n=node(m,'Custom');n.set_editor_property('description',label);n.set_editor_property('code',code)
    n.set_editor_property('include_file_paths',['/MingchaoSemantic/'+include])
    n.set_editor_property('output_type',getattr(unreal.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
    pins=[]
    for key in inputs:
        p=unreal.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
    n.set_editor_property('inputs',pins)
    for pair,pin in zip(inputs.values(),lib.get_material_expression_input_names(n)):wire(pair,n,str(pin))
    return n

def texture(m,key,path):
    t=unreal.load_asset(path);assert t,path
    n=node(m,'TextureObjectParameter');n.set_editor_property('parameter_name',key);n.set_editor_property('texture',t)
    n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if t.get_editor_property('srgb') else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    return (n,'')

def finish(m,name):
    lib.delete_unused_expressions(m)
    errors=list(lib.recompile_material(m));assert not errors,errors
    lib.layout_material_expressions(m);assert assets.save_loaded_asset(m)
    path=BASE+'/Instances/MI_SR_'+name
    instance=unreal.load_asset(path) or unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_SR_'+name,BASE+'/Instances',unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance,m);assert assets.save_loaded_asset(instance)
    return dict(material=m.get_path_name(),instance=instance.get_path_name(),errors=errors,nodes=lib.get_num_material_expressions(m))

def author(name):
    context()
    if name.startswith('UnderBase_'):
        part=name.split('_')[-1];path=BASE+'/M_SR_'+name
        assert not assets.does_asset_exist(path),'Do not overwrite an authored proxy without inspection'
        m=assets.duplicate_asset(BASE+'/M_SR_'+part,path)
        surface=next(n for n in lib.get_material_expressions(m) if isinstance(n,unreal.MaterialExpressionCustom) and ('return SR_FaceSurface(' in n.get_editor_property('code') or 'return SR_EyeSurface(' in n.get_editor_property('code')))
        output=custom(m,'Linear source base data; cancel capture pre-exposure','return Base/max(View.PreExposure,0.00000001);',{'Base':(surface,'')})
        lib.connect_material_property(output,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        return finish(m,name)
    m=create(name)
    if name.startswith('Outline_'):
        spec=json.loads((EVIDENCE/'outline_specs.json').read_text())
        s=next(p for p in spec['parts'] if p['name']==name[8:])
        m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
        uv=node(m,'TextureCoordinate');uv.set_editor_property('coordinate_index',1)
        vertex=node(m,'VertexColor')
        inputs={'OctUV':(uv,''),'VertexGreen':(vertex,'G'),'VertexBlue':(vertex,'B'),'Tangent':(node(m,'VertexTangentWS'),''),'Normal':(node(m,'VertexNormalWS'),''),'Position':(node(m,'WorldPosition'),''),'Camera':(node(m,'CameraPositionWS'),'')}
        for key,axis,space in [('Bitangent',[0,1,0],'TANGENT'),('ViewRight',[1,0,0],'VIEW'),('ViewUp',[0,1,0],'VIEW'),('ViewForward',[0,0,1],'VIEW')]:
            value=node(m,'Constant3Vector');value.set_editor_property('constant',unreal.LinearColor(*axis,0))
            transform=node(m,'Transform');transform.set_editor_property('transform_source_type',getattr(unreal.MaterialVectorCoordTransformSource,'TRANSFORMSOURCE_'+space));transform.set_editor_property('transform_type',unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD);wire((value,''),transform,'');inputs[key]=(transform,'')
        for key,value in dict(zip(['WidthFloor','Width','WidthClamp','DepthBias'],s['width']),DepthScale=s['depth'][0],WidthScale=1).items():inputs[key]=param(m,key,value)
        wpo=custom(m,'Current-view shell extrusion | E655 VS245-340','return SR_OutlineOffset(OctUV,VertexGreen,VertexBlue,Tangent,Bitangent,Normal,Camera-Position,dot(Position-Camera,ViewForward),ViewRight,ViewUp,1.0/float2(View.ViewToClip[0][0],View.ViewToClip[1][1]),View.ViewSizeAndInvSize.xy,WidthFloor,Width,WidthClamp,WidthScale,DepthBias,DepthScale);',inputs,include='Outline.ush')
        lib.connect_material_property(wpo,'',unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        if s['flat_color']:color=param(m,'SourceColor',s['flat_color'])
        else:
            uv=node(m,'TextureCoordinate')
            color=(custom(m,'Source outline color','return saturate(SR_SAMPLE_BIAS(ColorMap,ColorMapSampler,UV,0).rgb*Tint*Tint2);',{'ColorMap':texture(m,'ColorMap','/Game/MingchaoReverse/Textures/Character/'+s['textures']['t0']['name']),'UV':(uv,''),'Tint':param(m,'SourceTint',s['tint']),'Tint2':param(m,'SourceTint2',s['tint2'])}), '')
        out=custom(m,'Source ID13 light group','return Base*Light;',{'Base':color,'Light':param(m,'SourceID13Light',spec['light_scale'])})
        lib.connect_material_property(out,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        enabled=param(m,'OutlineEnabled',1);lib.connect_material_property(enabled[0],enabled[1],unreal.MaterialProperty.MP_OPACITY_MASK)
    else:
        m.set_editor_property('allow_negative_emissive_color',True)
        if name in ('FaceHET','EyeHET'):
            m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
            values=json.loads((ROOT/'Shaders/SemanticRebuild/AuxiliaryCalibration.json').read_text())[name]
            inputs={key:param(m,key,row['value']) for key,row in values.items()}
            setup='SR_HETSettings S;'+''.join('S.'+key+'='+key+';' for key in values)
            uv=node(m,'TextureCoordinate');vertex=node(m,'VertexColor');view=node(m,'CameraVectorWS');transform=node(m,'Transform')
            transform.set_editor_property('transform_source_type',unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD);transform.set_editor_property('transform_type',unreal.MaterialVectorCoordTransform.TRANSFORM_TANGENT);wire((view,''),transform,'')
            inputs.update(UV=(uv,''),ScreenUV=(node(m,'ScreenPosition'),'ViewportUV'),ViewTangent=(transform,''),VertexGreen=(vertex,'G'),Control=texture(m,'Control','/Game/MingchaoReverse/Textures/Character/T_HDMF_EM'),Region=texture(m,'Region','/Game/MingchaoReverse/Textures/Character/T_R2T1KatixiyaMd10011'+name[:-3]+'_HET'))
            coverage=custom(m,'Source HET coverage | E565/E577',setup+'float2 SearchUV;return SR_HETCoverage(Control,ControlSampler,Region,RegionSampler,UV,ScreenUV,View.ViewSizeAndInvSize.xy,ViewTangent,VertexGreen,'+('1' if name=='EyeHET' else '0')+',S,SearchUV);',inputs,size=1)
            lib.connect_material_property(coverage,'',unreal.MaterialProperty.MP_OPACITY_MASK)
        elif name=='BangsControl':
            offset=param(m,'ShadowOffsetLocalCm',[-0.13809600472450256,0,-0.10999999940395355])
            transform=node(m,'Transform');transform.set_editor_property('transform_source_type',unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL);transform.set_editor_property('transform_type',unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD);wire(offset,transform,'')
            lib.connect_material_property(transform,'',unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        else:raise ValueError(name)
        depth=custom(m,'Signed view depth in centimeters; cancel capture pre-exposure','return DepthSign*Depth/max(View.PreExposure,0.00000001);',{'Depth':(node(m,'PixelDepth'),''),'DepthSign':param(m,'DepthSign',-1 if name=='EyeHET' else 1)},size=1)
        lib.connect_material_property(depth,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return finish(m,name)

def bind():
    world,actors=context()
    parts={0:'Outline_Bangs',1:'Outline_Hair',2:'Outline_Face',3:'Outline_Up',4:'Outline_Down',7:'Outline_Item'}
    slots={'OutlineShell':parts,'HETProxy':{2:'FaceHET',6:'EyeHET'},'TintProxy':{2:'UnderBase_Face',6:'UnderBase_Eye'},'BangsProxy':{0:'BangsControl'}}
    bp=unreal.load_asset('/Game/MingchaoReverse/Blueprints/BP_U52AuxiliaryDriver')
    subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);blib=unreal.SubobjectDataBlueprintFunctionLibrary
    def apply(component,name,template=False):
        if name in slots:
            for slot in range(8):
                material=slots[name].get(slot)
                instance=unreal.load_asset(BASE+'/Instances/MI_SR_'+material if material else '/Game/MingchaoReverse/Materials/U52/M_U52_Hidden');assert instance,material
                component.set_material(slot,instance)
        if name in ('HETCapture','TintCapture','BangsCapture'):
            flags={str(s.show_flag_name):bool(s.enabled) for s in component.get_editor_property('show_flag_settings')}
            flags.update(Fog=False,Atmosphere=False,PostProcessing=False,EyeAdaptation=False,TemporalAA=False)
            notify=unreal.PropertyAccessChangeNotifyMode.DEFAULT if template else unreal.PropertyAccessChangeNotifyMode.NEVER
            component.set_editor_property('show_flag_settings',[unreal.EngineShowFlagsSetting(show_flag_name=k,enabled=v) for k,v in flags.items()],notify_mode=notify)
            component.set_editor_property('capture_every_frame',True,notify_mode=notify)
            component.set_editor_property('capture_sort_priority',3,notify_mode=notify)
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        obj=blib.get_object(blib.get_data(handle))
        if isinstance(obj,unreal.ActorComponent):apply(obj,obj.get_name().removesuffix('_GEN_VARIABLE'),True)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    world,actors=context()
    driver=actors['U52_AuxiliaryDriver']
    for component in driver.get_components_by_class(unreal.ActorComponent):apply(component,component.get_name())
    driver.call_method('RefreshAuxiliary')
    assert assets.save_loaded_asset(bp)
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    return {c.get_name():[c.get_material(i).get_path_name() for i in range(c.get_num_materials())] for c in driver.get_components_by_class(unreal.SkeletalMeshComponent)}
