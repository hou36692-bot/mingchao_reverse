#include "BangsViewCaptureComponent.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Math/RotationMatrix.h"
#include "SceneView.h"
#if WITH_EDITOR
#include "Editor.h"
#include "LevelEditorViewport.h"
#endif

UBangsViewCaptureComponent::UBangsViewCaptureComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bTickEvenWhenPaused = true;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
    bTickInEditor = true;
}

void UBangsViewCaptureComponent::OnRegister()
{
    Super::OnRegister();
#if WITH_EDITOR
    if (!IsTemplate() && GetWorld() && GetWorld()->WorldType == EWorldType::Editor)
    {
        CameraMovedHandle = FEditorDelegates::OnEditorCameraMoved.AddWeakLambda(
            this, [this](const FVector&, const FRotator&, ELevelViewportType, int32)
            {
                UpdateCurrentView();
            });
    }
#endif
    UpdateCurrentView();
}

void UBangsViewCaptureComponent::OnUnregister()
{
#if WITH_EDITOR
    FEditorDelegates::OnEditorCameraMoved.Remove(CameraMovedHandle);
    CameraMovedHandle.Reset();
#endif
    Super::OnUnregister();
}

void UBangsViewCaptureComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    UpdateCurrentView();
}

bool UBangsViewCaptureComponent::UpdateCurrentView()
{
    UWorld* World = GetWorld();
    if (!bFollowCurrentView || !World || IsTemplate())
    {
        return false;
    }
    if (World->IsGameWorld())
    {
        APlayerController* Player = World->GetFirstPlayerController();
        if (!Player || !Player->PlayerCameraManager)
        {
            return false;
        }
        const FMinimalViewInfo& View = Player->PlayerCameraManager->GetCameraCacheView();
        int32 Width = 0, Height = 0;
        Player->GetViewportSize(Width, Height);
        const float Aspect = View.bConstrainAspectRatio || Height <= 0 ? View.AspectRatio : float(Width) / Height;
        return UpdateForView(View.Location, View.Rotation, View.FOV, Aspect);
    }
#if WITH_EDITOR
    FLevelEditorViewportClient* Viewport = GCurrentLevelEditingViewportClient;
    if (World->WorldType == EWorldType::Editor && Viewport && Viewport->GetWorld() == World && Viewport->IsPerspective() && Viewport->Viewport)
    {
        const FIntPoint Size = Viewport->Viewport->GetSizeXY();
        if (Size.X > 0 && Size.Y > 0)
        {
            return UpdateForView(Viewport->GetViewLocation(), Viewport->GetViewRotation(), Viewport->ViewFOV, float(Size.X) / Size.Y);
        }
    }
#endif
    return false;
}

bool UBangsViewCaptureComponent::UpdateForView(FVector Location, FRotator Rotation, float HorizontalFOV, float AspectRatio)
{
    if (!GetWorld() || !GetOwner() || !CaptureParameters || Location.ContainsNaN() || Rotation.ContainsNaN()
        || !FMath::IsFinite(HorizontalFOV) || HorizontalFOV <= 0 || HorizontalFOV >= 179
        || !FMath::IsFinite(AspectRatio) || AspectRatio <= 0)
    {
        return false;
    }
    USceneCaptureComponent2D* HET = nullptr;
    USceneCaptureComponent2D* Tint = nullptr;
    TInlineComponentArray<USceneCaptureComponent2D*> Captures(GetOwner());
    for (USceneCaptureComponent2D* Capture : Captures)
    {
        if (Capture->GetFName() == TEXT("HETCapture")) HET = Capture;
        if (Capture->GetFName() == TEXT("TintCapture")) Tint = Capture;
    }
    if (!HET || !Tint || !HET->TextureTarget || !Tint->TextureTarget)
    {
        return false;
    }

    const double TanX = FMath::Tan(FMath::DegreesToRadians(double(HorizontalFOV) * 0.5));
    const double TanY = TanX / AspectRatio;
    const FMatrix Projection(
        FPlane(1.0 / TanX, 0, 0, 0),
        FPlane(0, 1.0 / TanY, 0, 0),
        FPlane(0, 0, 0, 1),
        FPlane(0, 0, GNearClippingPlane, 0));
    const FRotationMatrix Basis(Rotation);
    UMaterialParameterCollectionInstance* Parameters = GetWorld()->GetParameterCollectionInstance(CaptureParameters);
    if (!Parameters) return false;
    Parameters->SetVectorParameterValue(TEXT("BangsCaptureOrigin"), FLinearColor(Location.X, Location.Y, Location.Z, 1));
    const FVector Forward = Basis.GetUnitAxis(EAxis::X);
    const FVector Right = Basis.GetUnitAxis(EAxis::Y);
    const FVector Up = Basis.GetUnitAxis(EAxis::Z);
    Parameters->SetVectorParameterValue(TEXT("BangsCaptureForward"), FLinearColor(Forward.X, Forward.Y, Forward.Z, TanX));
    Parameters->SetVectorParameterValue(TEXT("BangsCaptureRight"), FLinearColor(Right.X, Right.Y, Right.Z, TanY));
    Parameters->SetVectorParameterValue(TEXT("BangsCaptureUp"), FLinearColor(Up.X, Up.Y, Up.Z, 0));
    Parameters->SetVectorParameterValue(TEXT("BangsCaptureRect"), FLinearColor(0, 0, 1, 1));

    // Both producers use this same view. BangsCapture keeps its reference shadow projection.
    // The RT dimensions stay unchanged; the matrix preserves the observing viewport's aspect.
    for (USceneCaptureComponent2D* Capture : {HET, Tint})
    {
        Capture->SetWorldLocationAndRotation(Location, Rotation);
        Capture->FOVAngle = HorizontalFOV;
        Capture->bUseCustomProjectionMatrix = true;
        Capture->CustomProjectionMatrix = Projection;
        Capture->CaptureSceneDeferred();
    }
    return true;
}
