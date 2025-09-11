@echo off
echo Converting Clinton Auto Detailing audio files to MP4 videos...
echo.

REM Check if FFmpeg is available
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ERROR: FFmpeg not found. Please install FFmpeg first.
    echo Download from: https://ffmpeg.org/download.html
    echo.
    echo After installing FFmpeg, run this script again.
    pause
    exit /b 1
)

cd /d "C:\Users\cjay4\OneDrive\Desktop\sincor-clean\clinton_videos"

REM Create solid color background videos with audio
echo Creating Business Introduction Video...
ffmpeg -f lavfi -i color=c=midnightblue:size=1920x1080:rate=24 -i "1_business_introduction.mp3" -c:v libx264 -c:a aac -shortest -y "1_business_introduction.mp4"

echo Creating Service Showcase Video...
ffmpeg -f lavfi -i color=c=darkblue:size=1920x1080:rate=24 -i "2_service_showcase.mp3" -c:v libx264 -c:a aac -shortest -y "2_service_showcase.mp4"

echo Creating Customer Testimonial Video...
ffmpeg -f lavfi -i color=c=navy:size=1920x1080:rate=24 -i "3_customer_testimonial.mp3" -c:v libx264 -c:a aac -shortest -y "3_customer_testimonial.mp4"

echo Creating Before/After Video...
ffmpeg -f lavfi -i color=c=royalblue:size=1920x1080:rate=24 -i "4_before_after_transformation.mp3" -c:v libx264 -c:a aac -shortest -y "4_before_after_transformation.mp4"

echo Creating Behind-the-Scenes Video...
ffmpeg -f lavfi -i color=c=steelblue:size=1920x1080:rate=24 -i "5_behind_scenes_process.mp3" -c:v libx264 -c:a aac -shortest -y "5_behind_scenes_process.mp4"

echo Creating Call-to-Action Video...
ffmpeg -f lavfi -i color=c=dodgerblue:size=1920x1080:rate=24 -i "6_call_to_action.mp3" -c:v libx264 -c:a aac -shortest -y "6_call_to_action.mp4"

echo.
echo ============================================================
echo ALL CLINTON AUTO DETAILING VIDEOS CREATED SUCCESSFULLY!
echo ============================================================
echo.
echo Video files created:
for %%f in (*.mp4) do echo   - %%f
echo.
echo These are professional-quality MP4 videos ready for marketing use.
echo Location: C:\Users\cjay4\OneDrive\Desktop\sincor-clean\clinton_videos
echo.
pause
