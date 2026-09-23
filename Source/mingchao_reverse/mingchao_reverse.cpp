// Fill out your copyright notice in the Description page of Project Settings.

#include "mingchao_reverse.h"
#include "Modules/ModuleManager.h"
#include "Misc/Paths.h"
#include "ShaderCore.h"

class FMingchaoReverseModule : public FDefaultGameModuleImpl
{
public:
	virtual void StartupModule() override
	{
		const FString VirtualDirectory = TEXT("/MingchaoSemantic");
		const FString SourceDirectory = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("Shaders/SemanticRebuild"));
		const FString* Existing = AllShaderSourceDirectoryMappings().Find(VirtualDirectory);
		checkf(!Existing || FPaths::IsSamePath(*Existing, SourceDirectory), TEXT("Conflicting /MingchaoSemantic shader source mapping"));
		if (!Existing)
		{
			AddShaderSourceDirectoryMapping(VirtualDirectory, SourceDirectory);
		}
	}
};

IMPLEMENT_PRIMARY_GAME_MODULE(FMingchaoReverseModule, mingchao_reverse, "mingchao_reverse");
