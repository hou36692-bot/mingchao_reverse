"""UE-MCP entry point for the R3 cloth materials. Never rebinds scene components."""
import json
import re
from pathlib import Path
import unreal


def author(name='Down', rebuild_owned=False):
    assert name in ('Down','Up','Item','Alpha','Face','Hair','Bangs'), 'Only source-traced contracts are authored'
    hair=name in ('Hair','Bangs')
    root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    assert root.as_posix().rstrip('/').lower()=='d:/ue_project/mingchao_reverse'
    base='/Game/MingchaoReverse/Materials/SemanticRebuild'
    lib=unreal.MaterialEditingLibrary
    assets=unreal.EditorAssetLibrary
    material=unreal.load_asset(base+'/M_SR_'+name)
    if material:
        assert not any(isinstance(n, unreal.MaterialExpressionStaticSwitchParameter) and str(n.get_editor_property('parameter_name')) == 'CurrentViewRimOverlay' for n in lib.get_material_expressions(material)), 'Current-view rim graph is already installed; this legacy builder must not overwrite it.'
        assert rebuild_owned, 'Existing material requires explicit rebuild_owned'
        for expression in list(lib.get_material_expressions(material)):
            lib.delete_material_expression(material,expression)
    else:
        material=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_SR_'+name,base,unreal.Material,unreal.MaterialFactoryNew())
    material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('used_with_skeletal_mesh',True)
    if name=='Alpha':
        material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
        material.set_editor_property('opacity_mask_clip_value',0.5)
    calibration=json.loads((root/f'Shaders/SemanticRebuild/{name}Calibration.json').read_text())
    parameters={}
    rows={}
    def node(kind,x=0,y=0):
        return lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind),x,y)
    def wire(source,target,pin):
        assert lib.connect_material_expressions(source[0],source[1],target,pin),str(pin)
    def parameter(key):
        if key in parameters:return parameters[key]
        item=calibration[key];v=item['value'];group=item['group'];row=rows.get(group,0);rows[group]=row+1
        x=-3500+int(group[:2])*380;y=1400+row*170
        n=node('VectorParameter' if isinstance(v,list) else 'ScalarParameter',x,y)
        parameter_name='UseIDRegion' if name=='Up' and key=='UseVertexRegion' else key
        for p,value in [('parameter_name',parameter_name),('group',group),('sort_priority',row),('desc',item['meaning']+'; '+item['source'])]:n.set_editor_property(p,value)
        if isinstance(v,list):
            n.set_editor_property('default_value',unreal.LinearColor(*(v+[0]*(4-len(v)))))
            result=(n,'RGBA' if len(v)==4 else 'RGB')
            if len(v)==2:
                m=node('ComponentMask',x+190,y)
                for c,on in zip('rgba',(True,True,False,False)):m.set_editor_property(c,on)
                wire(result,m,'');result=(m,'')
        else:n.set_editor_property('default_value',v);result=(n,'')
        parameters[key]=result
        return result
    def custom(label,code,inputs,outputs=None,size=3,include='Cloth.ush',x=0,y=0):
        n=node('Custom',x,y);n.set_editor_property('description',label);n.set_editor_property('code',code)
        n.set_editor_property('include_file_paths',['/MingchaoSemantic/'+include])
        n.set_editor_property('output_type',getattr(unreal.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
        pins=[]
        for key in inputs:
            p=unreal.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
        n.set_editor_property('inputs',pins)
        extra=[]
        for key,count in (outputs or {}).items():
            p=unreal.CustomOutput();p.set_editor_property('output_name',key);p.set_editor_property('output_type',getattr(unreal.CustomMaterialOutputType,'CMOT_FLOAT'+str(count)));extra.append(p)
        n.set_editor_property('additional_outputs',extra)
        actual=lib.get_material_expression_input_names(n)
        assert len(actual)==len(inputs)
        for source,pin in zip(inputs.values(),actual):wire(source,n,str(pin))
        return n
    def settings(kind,file,var='S'):
        source=(root/'Shaders/SemanticRebuild'/file).read_text()
        body=re.search(r'struct '+kind+r'\s*\{(.*?)\};',source,re.S)[1]
        names=re.findall(r'float[234]?\s+(\w+)\s*;',body)
        return kind+' '+var+';'+''.join(var+'.'+n+'='+('0' if name=='Up' and n=='RampBlend' else n)+';' for n in names),{n:parameter(n) for n in names if not(name=='Up' and n=='RampBlend')}
    def texture(key,path,srgb,source_copy=False):
        t=unreal.load_asset(path);assert t,path
        # R32F has no sRGB view; its inherited Texture.SRGB flag is not the format contract.
        if isinstance(t,unreal.TextureRenderTarget2D):
            assert t.get_editor_property('render_target_format')==(unreal.TextureRenderTargetFormat.RTF_RGBA8 if key=='UnderBase' else unreal.TextureRenderTargetFormat.RTF_R32F),path
        else:
            assert t.get_editor_property('srgb')==srgb,path
        if source_copy:
            destination='/Game/MingchaoReverse/Textures/SemanticRebuild/'+path.rsplit('/',1)[1]+('_Mask_SR' if key=='MaskMap' else '_SR')
            t=unreal.load_asset(destination) or assets.duplicate_asset(path,destination)
            address=unreal.TextureAddress.TA_CLAMP if key in ('SkinRamp','MarkMap','MaskMap','LightMap') else unreal.TextureAddress.TA_WRAP
            t.set_editor_property('address_x',address);t.set_editor_property('address_y',address)
            t.set_editor_property('filter',unreal.TextureFilter.TF_TRILINEAR if key in ('LookupMap','MarkMap','NoiseA','NoiseB','LightMap') else unreal.TextureFilter.TF_BILINEAR)
            if key in ('SkinRamp','NoiseMap','MaskMap','LightMap','HairMask'):t.set_editor_property('mip_gen_settings',unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
            assets.save_loaded_asset(t)
        n=node('TextureObjectParameter',-2200,-1000+len(textures)*170)
        n.set_editor_property('parameter_name',key);n.set_editor_property('texture',t);n.set_editor_property('group','00 Source textures')
        n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if srgb else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        textures[key]=(n,'');return (n,'')
    collection=unreal.load_asset('/Game/MingchaoReverse/Materials/U2/MPC_ReferenceScene')
    def scene(key):
        n=node('CollectionParameter',-2500,-1200-len(parameters)*5);n.set_editor_property('collection',collection);n.set_editor_property('parameter_name',key)
        return (n,'')
    textures={}
    source_textures=[('PackedMap','T_R2T1KatixiyaMd10011'+name+'_N',False),('ColorMap','T_R2T1KatixiyaMd10011'+name+'_D',True),('LookupMap','T_MC_premake_D',True),('SkinRamp','T_R2T1KatixiyaMd10011_Skin',True)]+([('IDMap','T_R2T1KatixiyaMd10011Up_ID',False)] if name=='Up' else [])
    if name=='Face':
        source_textures=[('MarkMap','T_6XingStar02_D',True),('NoiseA','T_XingHenSoundNoise',False),('NoiseB','T_XingHenSoundNoise02',False),('IDMap','T_R2T1KatixiyaMd10011Face_ID',False),('ColorMap','T_R2T1KatixiyaMd10011Face_D',True),('MaskMap','T_FemaleMFace_SDF',False),('LightMap','T_FemaleMFace_SDF',False),('SkinRamp','T_R2T1KatixiyaMd10011_Skin',True)]
    if hair:
        source_textures=[('ColorMap','T_R2T1KatixiyaMd10011'+name+'_D',True),('HairMask','T_R2T1KatixiyaMd10011'+name+'_HM',False),('SkinRamp','T_R2T1KatixiyaMd10011_Skin',True)]
    for key,file,srgb in source_textures:
        texture(key,'/Game/MingchaoReverse/Textures/Character/'+file,srgb,True)
    if name=='Item':
        for key,file in [('LayerMap','T_Dissovlve_30005'),('PatternMap','T_Wenli_Katixiya_140001')]:
            texture(key,'/Game/MingchaoReverse/Textures/Character/'+file,True,True)
    if name=='Alpha':
        texture('NoiseMap','/Game/MingchaoReverse/Textures/Character/Good64x64TilingNoiseHighFreq',False,True)
    uv=node('TextureCoordinate',-2600,-900);vertex=node('VertexColor',-2600,-700)
    normal=node('VertexNormalWS',-2600,-500);tangent=node('VertexTangentWS',-2600,-300)
    axis=node('Constant3Vector',-2900,-100);axis.set_editor_property('constant',unreal.LinearColor(0,1,0,0))
    bitangent=node('Transform',-2600,-100)
    bitangent.set_editor_property('transform_source_type',unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT)
    bitangent.set_editor_property('transform_type',unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD);wire((axis,''),bitangent,'')
    view=node('CameraVectorWS',-2600,100);position=node('WorldPosition',-2600,300);depth=node('PixelDepth',-2600,500)
    view_axes={}
    for i,key in enumerate(['ViewRight','ViewUp','ViewForward']):
        a=node('Constant3Vector',-2600,700+i*170);values=[0,0,0];values[i]=1;a.set_editor_property('constant',unreal.LinearColor(*values,0))
        n=node('Transform',-2300,700+i*170)
        n.set_editor_property('transform_source_type',unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_VIEW)
        n.set_editor_property('transform_type',unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD);wire((a,''),n,'');view_axes[key]=(n,'')
    body,inputs=settings('SR_HairSettings' if hair else ('SR_FaceSettings' if name=='Face' else 'SR_ClothSettings'),'Hair.ush' if hair else ('Face.ush' if name=='Face' else 'Cloth.ush'))
    inputs.update(textures);inputs.update(UV=(uv,''),VertexEmission=parameter('VertexEmission'),VertexNormal=(normal,''),StyleLight=scene('LightDirection'),FlatLight=scene('LightDirectionFlat'))
    if name!='Face':
        inputs.update(VertexRed=(vertex,'R'),Tangent=(tangent,''),Bitangent=(bitangent,''),View=(view,''));inputs.update(view_axes)
    if hair:
        call='SR_HairSurface(ColorMap,ColorMapSampler,HairMask,HairMaskSampler,SkinRamp,SkinRampSampler,UV,VertexRed,VertexEmission,VertexNormal,View,StyleLight.xyz,FlatLight.xyz,S,Normal,SecondaryTint,Emission,LightMask,Regions,Highlight,LookupUV,ColorAlpha)'
    elif name=='Face':
        mark_uv=node('TextureCoordinate',-2900,-700);mark_uv.set_editor_property('coordinate_index',3)
        inputs.update(UV3=(mark_uv,''),HeadForward=scene('HeadForward'),HeadRight=scene('HeadRight'))
        clock=node('Time',-2900,200)
        clock_input=custom('Clock: source time plus optional playback','return TimeSeconds+Elapsed*AnimationRate;',{'TimeSeconds':parameter('TimeSeconds'),'Elapsed':(clock,''),'AnimationRate':parameter('AnimationRate')},size=1,x=-2200,y=200)
        inputs['Clock']=(clock_input,'')
        call='SR_FaceSurface(MarkMap,MarkMapSampler,NoiseA,NoiseASampler,NoiseB,NoiseBSampler,IDMap,IDMapSampler,ColorMap,ColorMapSampler,MaskMap,MaskMapSampler,LightMap,LightMapSampler,SkinRamp,SkinRampSampler,UV,UV3.x,VertexEmission,Clock,VertexNormal,StyleLight.xyz,FlatLight.xyz,HeadForward.xyz,HeadRight.xyz,S,Normal,SecondaryTint,Emission,LightMask,Regions,Highlight,LookupUV)'
    elif name=='Up':
        extra,up_inputs=settings('SR_UpSettings','Up.ush','U');body+=extra;inputs.update(up_inputs)
        inputs.pop('VertexRed')
        call='SR_UpSurface(PackedMap,PackedMapSampler,IDMap,IDMapSampler,ColorMap,ColorMapSampler,LookupMap,LookupMapSampler,SkinRamp,SkinRampSampler,UV,VertexEmission,Tangent,Bitangent,VertexNormal,View,StyleLight.xyz,FlatLight.xyz,ViewRight,ViewUp,ViewForward,S,U,Normal,SecondaryTint,Emission,LightMask,Regions,Highlight,LookupUV)'
    elif name=='Item':
        extra,item_inputs=settings('SR_ItemSettings','Item.ush','I');body+=extra;inputs.update(item_inputs)
        for i in (1,2,3):
            n=node('TextureCoordinate',-2900,-900+i*170);n.set_editor_property('coordinate_index',i);inputs['UV'+str(i)]=(n,'')
        screen=node('ScreenPosition',-2900,0);inputs['ScreenUV']=(screen,'ViewportUV')
        clock=node('Time',-2900,200)
        clock_input=custom('Clock: source time plus optional playback','return TimeSeconds+Elapsed*AnimationRate;',{'TimeSeconds':parameter('TimeSeconds'),'Elapsed':(clock,''),'AnimationRate':parameter('AnimationRate')},size=1,x=-2200,y=200)
        inputs['Clock']=(clock_input,'')
        call='SR_ItemSurface(PackedMap,PackedMapSampler,ColorMap,ColorMapSampler,LayerMap,LayerMapSampler,PatternMap,PatternMapSampler,LookupMap,LookupMapSampler,SkinRamp,SkinRampSampler,UV,UV1,UV2,UV3,ScreenUV,Clock,VertexRed,VertexEmission,Tangent,Bitangent,VertexNormal,View,StyleLight.xyz,FlatLight.xyz,ViewRight,ViewUp,ViewForward,S,I,Normal,SecondaryTint,Emission,LightMask,Regions,Highlight,LookupUV)'
    else:
        call='SR_ClothSurface(PackedMap,PackedMapSampler,ColorMap,ColorMapSampler,LookupMap,LookupMapSampler,SkinRamp,SkinRampSampler,UV,VertexRed,VertexEmission,Tangent,Bitangent,VertexNormal,View,StyleLight.xyz,FlatLight.xyz,ViewRight,ViewUp,ViewForward,S,Normal,SecondaryTint,Emission,LightMask,Regions,Highlight,LookupUV)'
    outputs={'Normal':3,'SecondaryTint':3,'Emission':3,'LightMask':1,'Regions':2,'Highlight':1,'LookupUV':2}
    if hair:outputs['ColorAlpha']=1
    surface=custom('01 Surface | '+{'Down':'E488 0-293','Up':'E528 0-372','Item':'E509 0-348','Alpha':'E473 0-324','Face':'E454 0-302','Hair':'E621 9-179','Bangs':'E611 9-179'}[name],body+'return '+call+';',inputs,outputs,include={'Down':'Cloth.ush','Up':'Up.ush','Item':'Item.ush','Alpha':'Alpha.ush','Face':'Face.ush','Hair':'Hair.ush','Bangs':'Hair.ush'}[name],x=-1000,y=-400)
    if name=='Alpha':
        body,inputs=settings('SR_AlphaSettings','Alpha.ush','A')
        screen=node('ScreenPosition',-2000,-1400)
        inputs.update(UV=(uv,''),ScreenUV=(screen,'ViewportUV'),ColorMap=textures['ColorMap'],NoiseMap=textures['NoiseMap'],AlphaGain=parameter('AlphaGain'),MipBias=parameter('MipBias'))
        coverage=custom('Coverage | E473 272-301',body+'return SR_AlphaCoverage(ColorMap,ColorMapSampler,NoiseMap,NoiseMapSampler,UV,ScreenUV*View.ViewSizeAndInvSize.xy,Parameters.SvPosition.xy,AlphaGain,MipBias,A,SignedCoverage);',inputs,{'SignedCoverage':1},size=1,include='Alpha.ush',x=-1000,y=-1400)
        assert lib.connect_material_property(coverage,'',unreal.MaterialProperty.MP_OPACITY_MASK)
    capture={'WorldPosition':(position,''),'CaptureOrigin':scene('ReferenceCamera')}
    capture.update({k:parameter(k) for k in ['CaptureForward','CaptureRight','CaptureUp','CaptureTanHalfFov']})
    source_base=(surface,'')
    if name=='Bangs':
        inputs=dict(capture);inputs.update(HETDepth=texture('HETDepth','/Game/MingchaoReverse/Materials/U52/Runtime/RT_U52_HETDepth',False),UnderBase=texture('UnderBase','/Game/MingchaoReverse/Materials/U52/Runtime/RT_U52_SourceTint',False),Base=source_base,ColorAlpha=(surface,'ColorAlpha'),HairAlphaScale=parameter('HairAlphaScale'),Enabled=parameter('HairBlendEnabled'))
        blend=custom('02 Local bangs base blend | E711','return SR_BlendBangsBase(HETDepth,UnderBase,WorldPosition,CaptureOrigin.xyz,CaptureForward,CaptureRight,CaptureUp,CaptureTanHalfFov,Base,ColorAlpha,HairAlphaScale,Enabled,HairRegion,HairAlpha);',inputs,{'HairRegion':1,'HairAlpha':1},include='Hair.ush',x=-400,y=-600)
        source_base=(blend,'')
    inputs=dict(capture);inputs['SurfaceMask']=(surface,'LightMask')
    if not hair:
        inputs.update(BangsDepth=texture('BangsDepth','/Game/MingchaoReverse/Materials/U52/Runtime/RT_U52_BangsDepth',False),Enabled=parameter('BangsShadowEnabled'))
    auxiliary=custom('02 Existing U52 depth adapter','Occluded=0;return SurfaceMask;' if hair else 'return SR_ApplyBangsShadow(BangsDepth,WorldPosition,CaptureOrigin.xyz,CaptureForward,CaptureRight,CaptureUp,CaptureTanHalfFov,Enabled,SurfaceMask,Occluded);',inputs,{'Occluded':1},size=1,include='CharacterLighting.ush',x=-200,y=-800)
    body,inputs=settings('SR_CharacterLightSettings','CharacterLighting.ush')
    inputs.update(Base=source_base,SecondaryTint=(surface,'SecondaryTint'),LightMask=(auxiliary,''),ExtraControl=parameter('ExtraControl'),Visibility=parameter('Visibility'),ViewDepthCm=(depth,''))
    light=custom('03 Character lighting | E1401 246-318',body+'return SR_EvaluateCharacterLighting(Base,SecondaryTint,LightMask,ExtraControl,Visibility,ViewDepthCm,S,Shadow,Secondary,Bright);',inputs,{'Shadow':3,'Secondary':3,'Bright':1},include='CharacterLighting.ush',x=600,y=-400)
    body,inputs=settings('SR_DepthRimSettings','DepthRim.ush');inputs.update(capture)
    inputs.update(CharacterDepth=texture('CharacterDepth','/Game/MingchaoReverse/Materials/U2/Runtime/RT_CharacterDepth',False),Base=source_base,Normal=(surface,'Normal'))
    rim=custom('04 Depth rim | E1401 436-561',body+'return SR_EvaluateDepthRim(CharacterDepth,CharacterDepthSampler,WorldPosition,Normal,Base,CaptureOrigin.xyz,CaptureForward,CaptureRight,CaptureUp,CaptureTanHalfFov,S,EdgeMask);',inputs,{'EdgeMask':1},include='DepthRim.ush',x=600,y=0)
    inputs={'Mode':parameter('DebugMode'),'Base':source_base,'Tint':(surface,'SecondaryTint'),'Normal':(surface,'Normal'),'Mask':(auxiliary,''),'Emission':(surface,'Emission'),'Region':(surface,'Regions'),'Highlight':(surface,'Highlight'),'Lookup':(surface,'LookupUV'),'Light':(light,''),'Rim':(rim,''),'Occlusion':(auxiliary,'Occluded'),'RimEnabled':scene('RimEnabled'),'Exposure':scene('ExposureScale')}
    output=custom('05 Final and diagnostics','if(Mode<0.5)return max(Light+Emission+Rim*RimEnabled,0)*Exposure;if(Mode<1.5)return Base;if(Mode<2.5)return Tint;if(Mode<3.5)return Normal*0.5+0.5;if(Mode<4.5)return Mask.xxx;if(Mode<5.5)return Emission;if(Mode<6.5)return float3(Region,0);if(Mode<7.5)return Highlight.xxx;if(Mode<8.5)return float3(Lookup,0);if(Mode<9.5)return Rim;return Occlusion.xxx;',inputs,x=1400,y=-400)
    assert lib.connect_material_property(output,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(material)
    instance=unreal.load_asset(base+'/Instances/MI_SR_'+name) or unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_SR_'+name,base+'/Instances',unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance,material)
    assets.save_loaded_asset(material);assets.save_loaded_asset(instance)
    return dict(material=material.get_path_name(),instance=instance.get_path_name(),parameters=len(parameters),binding_changed=False)
