#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "BangsViewCaptureComponent.generated.h"

class UMaterialParameterCollection;

/** Keeps the existing HET and SourceBase producers aligned with the observing camera. */
UCLASS(ClassGroup=(Rendering), meta=(BlueprintSpawnableComponent))
class MINGCHAO_REVERSE_API UBangsViewCaptureComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UBangsViewCaptureComponent();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Bangs capture")
    TObjectPtr<UMaterialParameterCollection> CaptureParameters;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Bangs capture")
    bool bFollowCurrentView = true;

    UFUNCTION(BlueprintCallable, CallInEditor, Category="Bangs capture")
    bool UpdateCurrentView();

    /** Also used for isolated offscreen validation with the same producer contract. */
    UFUNCTION(BlueprintCallable, Category="Bangs capture")
    bool UpdateForView(FVector Location, FRotator Rotation, float HorizontalFOV, float AspectRatio);

protected:
    virtual void OnRegister() override;
    virtual void OnUnregister() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

#if WITH_EDITOR
    FDelegateHandle CameraMovedHandle;
#endif
};
