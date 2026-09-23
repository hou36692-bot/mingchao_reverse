"""Build one semantic background material, then bind only its existing component."""
import json,runpy
from pathlib import Path
import unreal

ROOT=Path('D:/UE_Project/mingchao_reverse')
OUT=Path('D:/HOU/mingchao_reverse/assets/shader_rebuild')
BASE='/Game/MingchaoReverse/Materials/SemanticRebuild'
HELP=runpy.run_path(str(Path(__file__).with_name('author_auxiliary.py')))
lib=unreal.MaterialEditingLibrary;assets=unreal.EditorAssetLibrary
node=HELP['node'];wire=HELP['wire'];custom=HELP['custom']

def param(m,key,value,group='01 Shape and color'):
    pair=HELP['param'](m,key,value,group)
    if isinstance(value,list) and len(value)==4:
        append=node(m,'AppendVector');wire(pair,append,'A');wire((pair[0],'A'),append,'B');return (append,'')
    return pair

FAMILIES={415:'Sky',1589:'Nebula',1674:'Cloud',1683:'Cloud',1692:'Cloud',1701:'Cloud',1718:'Flow',1743:'AlphaFlow',1793:'Ribbon',1768:'Fog',1772:'FogBack',1817:'Particle',1821:'Particle',1638:'Floor'}

def projection():
    world,actors=HELP['context']();c=actors['U4_FloorReflectionCapture'].get_component_by_class(unreal.SceneCaptureComponent2D)
    path=BASE+'/MPC_ReflectionView';collection=unreal.load_asset(path)
    assert not collection,'Preserve existing collection parameter identities'
    collection=unreal.AssetToolsHelpers.get_asset_tools().create_asset('MPC_ReflectionView',BASE,unreal.MaterialParameterCollection,unreal.MaterialParameterCollectionFactoryNew())
    vectors={'ReflectionPosition':c.get_world_location(),'ReflectionRight':c.get_right_vector(),'ReflectionUp':c.get_up_vector(),'ReflectionForward':c.get_forward_vector()}
    entries=[]
    for key,v in vectors.items():
        n=unreal.CollectionVectorParameter();n.set_editor_property('parameter_name',key);n.set_editor_property('default_value',unreal.LinearColor(v.x,v.y,v.z,0));entries.append(n)
    collection.set_editor_property('vector_parameters',entries)
    scalars={'ReflectionFOV':c.fov_angle,'ReflectionAspect':c.texture_target.size_x/c.texture_target.size_y};entries=[]
    for key,value in scalars.items():
        n=unreal.CollectionScalarParameter();n.set_editor_property('parameter_name',key);n.set_editor_property('default_value',value);entries.append(n)
    collection.set_editor_property('scalar_parameters',entries);assert assets.save_loaded_asset(collection)
    data={'vectors':{k:[v.x,v.y,v.z] for k,v in vectors.items()},'scalars':scalars,'capture':c.get_path_name(),'target':c.texture_target.get_path_name(),'size':[c.texture_target.size_x,c.texture_target.size_y]}
    (OUT/'r6_reflection_view.json').write_text(json.dumps(data,indent=2));return data

def author(event=415,instance=0):
    world,actors=HELP['context']()
    row=next(r for r in json.loads((OUT/'r6_original_bindings.json').read_text()) if r['label'].startswith(f'U4_E{event}_I{instance}_'))
    family=FAMILIES[event];name=f'BG_{family}_E{event}_I{instance}'
    m=HELP['create'](name);m.set_editor_property('used_with_skeletal_mesh',False)
    source=unreal.load_asset(row['parent'])
    for key in ['blend_mode','two_sided','translucency_pass']:m.set_editor_property(key,source.get_editor_property(key))
    table=json.loads((ROOT/'Shaders/SemanticRebuild/BackgroundCalibration.json').read_text())[family]
    inputs={key:param(m,key,data['value']) for key,data in table.items()}
    settings='SR_'+family+'Settings S;'+''.join('S.'+key+'='+key+';' for key in table)
    inputs.update({key:HELP['texture'](m,key,path) for key,path in row['textures'].items()})
    inputs.update(UV=(node(m,'TextureCoordinate'),''),SourceTime=param(m,'SourceTime',row['scalars']['SourceTime'],'02 Time'),LayerIntensity=param(m,'LayerIntensity',row['scalars']['LayerIntensity'],'03 Layer'))
    if family=='Sky':
        inputs.update(ScreenUV=(node(m,'ScreenPosition'),'ViewportUV'),WorldRay=(node(m,'WorldPosition'),''))
        call='SR_Sky(t0,t0Sampler,t1,t1Sampler,t2,t2Sampler,t3,t3Sampler,t4,t4Sampler,UV,ScreenUV.y,WorldRay,SourceTime,S)'
    elif family=='Nebula':
        inputs['FogTransmission']=param(m,'FogTransmission',row['vectors']['V3'][3],'04 Frozen source instance')
        call='SR_Nebula(t1,t1Sampler,t2,t2Sampler,t3,t3Sampler,t4,t4Sampler,UV,FogTransmission,SourceTime,S)'
    elif family=='Cloud':
        inputs.update(DepthCm=(node(m,'PixelDepth'),''),SceneDepthCm=(node(m,'SceneDepth'),''),ViewDirection=(node(m,'CameraVectorWS'),''),Normal=(node(m,'VertexNormalWS'),''),InstanceColor=param(m,'InstanceColor',row['vectors']['V4'],'04 Frozen source instance'))
        call='SR_Cloud(t3,t3Sampler,t4,t4Sampler,t5,t5Sampler,t6,t6Sampler,UV,SourceTime,DepthCm,SceneDepthCm,ViewDirection,Normal,InstanceColor,S)'
    elif family in ('Flow','Ribbon','AlphaFlow'):
        inputs.update(ScreenUV=(node(m,'ScreenPosition'),'ViewportUV'),DepthCm=(node(m,'PixelDepth'),''),SceneDepthCm=(node(m,'SceneDepth'),''),ViewDirection=(node(m,'CameraVectorWS'),''),Normal=(node(m,'VertexNormalWS'),''),InstanceColor=param(m,'InstanceColor',row['vectors']['V4'],'04 Frozen source instance'),InstanceMotion=param(m,'InstanceMotion',row['vectors']['V5'] if family=='Ribbon' else [0,0,1,1],'04 Frozen source instance'))
        textures='t2,t2Sampler,t4,t4Sampler,t5,t5Sampler,t6,t6Sampler' if family=='AlphaFlow' else 't2,t2Sampler,t3,t3Sampler,t4,t4Sampler,t5,t5Sampler'
        call=f'SR_Flow({textures},UV,ScreenUV,SourceTime,DepthCm,SceneDepthCm,ViewDirection,Normal,InstanceColor,InstanceMotion,{1 if family=="AlphaFlow" else 0},S)'
    elif family in ('Fog','FogBack'):
        inputs.update(InstanceColor=param(m,'InstanceColor',row['vectors']['V5'],'04 Frozen source instance'),InstanceMotion=param(m,'InstanceMotion',row['vectors']['V6'][:2] if family=='Fog' else [0,0],'04 Frozen source instance'))
        call='SR_Fog(t1,t1Sampler,t2,t2Sampler,t3,t3Sampler,UV,SourceTime,InstanceColor,InstanceMotion,S)'
    elif family=='Particle':
        inputs['UV'][0].set_editor_property('coordinate_index',1)
        inputs.update(DepthCm=(node(m,'PixelDepth'),''),InstanceColor=param(m,'InstanceColor',row['vectors']['V4'],'04 Frozen source instance'),InstanceOffset=param(m,'InstanceOffset',row['vectors']['V5'][0],'04 Frozen source instance'),InstanceDissolve=param(m,'InstanceDissolve',row['vectors']['V6'][:3],'04 Frozen source instance'))
        call='SR_Particle(t1,t1Sampler,t2,t2Sampler,UV,SourceTime,DepthCm,InstanceColor,InstanceOffset,InstanceDissolve,S)'
    elif family=='Floor':
        uv1=node(m,'TextureCoordinate');uv1.set_editor_property('coordinate_index',1);inputs['UV1']=(uv1,'');inputs['WorldPosition']=(node(m,'WorldPosition'),'')
        collection=unreal.load_asset(BASE+'/MPC_ReflectionView');assert collection
        for key in ['ReflectionPosition','ReflectionRight','ReflectionUp','ReflectionForward','ReflectionFOV','ReflectionAspect']:
            n=node(m,'CollectionParameter');n.set_editor_property('collection',collection);n.set_editor_property('parameter_name',key);inputs[key]=(n,'')
        settings+='float ReflectionValid;float2 ReflectionUV=SR_ReflectionUV(WorldPosition,ReflectionPosition.rgb,ReflectionRight.rgb,ReflectionUp.rgb,ReflectionForward.rgb,ReflectionFOV,ReflectionAspect,ReflectionValid);'
        call='SR_Floor(t0,t0Sampler,t2,t2Sampler,t3,t3Sampler,SR_FloorUV(UV,UV1),ReflectionUV,ReflectionValid,SourceTime,S)'
    shader=custom(m,'Semantic '+family,settings+'float4 Result='+call+';return float4(Result.rgb*LayerIntensity,Result.a);',inputs,size=4,include='Background.ush')
    rgb=node(m,'ComponentMask')
    for key,value in zip('rgba',[True,True,True,False]):rgb.set_editor_property(key,value)
    wire((shader,''),rgb,'');lib.connect_material_property(rgb,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if event!=415:
        enabled=param(m,'LayerEnabled',row['scalars']['LayerEnabled'],'03 Layer')
        if event in (1638,1743,1817,1821):
            alpha=node(m,'ComponentMask')
            for key,value in zip('rgba',[False,False,False,True]):alpha.set_editor_property(key,value)
            wire((shader,''),alpha,'');mul=node(m,'Multiply');wire((alpha,''),mul,'A');wire(enabled,mul,'B');enabled=(mul,'')
        lib.connect_material_property(enabled[0],enabled[1],unreal.MaterialProperty.MP_OPACITY)
    if family=='Particle':
        table=json.loads((ROOT/'Shaders/SemanticRebuild/ParticleWPOCalibration.json').read_text())[f'E{event}_I{instance}']
        winputs={key:param(m,key,value,'05 Billboard state') for key,value in table.items()}
        winputs.update(UV0=(node(m,'TextureCoordinate'),''),LocalPosition=(node(m,'PreSkinnedPosition'),''),WorldPosition=(node(m,'WorldPosition'),''),Camera=(node(m,'CameraPositionWS'),''),VertexRed=(node(m,'VertexColor'),'R'))
        setup='SR_ParticleWPOSettings S;'+''.join('S.'+key+'='+key+';' for key in table)
        wpo=custom(m,'Source fixed particle billboard | E1817/E1821 VS514-599',setup+'return SR_ParticleOffset(LocalPosition,WorldPosition,Camera,UV0,VertexRed,S);',winputs,size=3,include='Particle.ush')
        lib.connect_material_property(wpo,'',unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    result=HELP['finish'](m,name)
    if event in (1718,1743):preserve_affine(event)
    return result

def bind(event=415,instance=0):
    world,actors=HELP['context']()
    actor=next(a for label,a in actors.items() if label.startswith(f'U4_E{event}_I{instance}_'))
    material=unreal.load_asset(BASE+f'/Instances/MI_SR_BG_{FAMILIES[event]}_E{event}_I{instance}');assert material
    c=actor.get_component_by_class(unreal.StaticMeshComponent);c.set_material(0,material)
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    return {'component':c.get_path_name(),'material':c.get_material(0).get_path_name()}

def preserve_affine(event=1718):
    """Retain the two source affine corrections lost by TRS decomposition."""
    assert event in (1718,1743)
    HELP['context']()
    row=next(r for r in json.loads((OUT/'r6_original_bindings.json').read_text()) if r['label'].startswith(f'U4_E{event}_I0_'))
    source=unreal.load_asset(row['parent'])
    old=next(n for n in lib.get_material_expressions(source) if isinstance(n,unreal.MaterialExpressionCustom) and len(n.get_editor_property('code'))<1000)
    code=old.get_editor_property('code')
    assert code.startswith('return LocalPosition.x*float3(') and code.endswith('-WorldPosition;')
    name=f'BG_{FAMILIES[event]}_E{event}_I0';m=unreal.load_asset(BASE+'/M_SR_'+name)
    assert not any(isinstance(n,unreal.MaterialExpressionCustom) and n.get_editor_property('description')=='Retained source affine correction' for n in lib.get_material_expressions(m))
    n=custom(m,'Retained source affine correction',code,{'LocalPosition':(node(m,'PreSkinnedPosition'),''),'WorldPosition':(node(m,'WorldPosition'),'')},size=3,include='Background.ush')
    assert lib.connect_material_property(n,'',unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    errors=lib.recompile_material(m);assert not errors,str(errors)[:1500]
    assert assets.save_loaded_asset(m)
    return {'event':event,'retained_short_code':code}
