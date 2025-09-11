"""
Clinton Auto Detailing - FREE Video Generator
Uses MoviePy and gTTS for immediate MP4 creation
No API keys required - generates actual video files
"""

import os
import sys
from pathlib import Path

# Install required packages
def install_requirements():
    """Install required packages for video generation"""
    packages = [
        "moviepy",
        "gtts",
        "pillow",
        "numpy"
    ]
    
    for package in packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"[OK] {package} already installed")
        except ImportError:
            print(f"Installing {package}...")
            os.system(f"pip install {package}")

# Check and install requirements
install_requirements()

# Now import the packages
try:
    from moviepy.editor import *
    from gtts import gTTS
    import tempfile
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Run: pip install moviepy gtts pillow numpy")
    sys.exit(1)

class ClintonVideoGeneratorFree:
    def __init__(self):
        self.business_name = "Clinton Auto Detailing"
        self.phone = "(815) 718-8936"
        self.location = "Clinton, IL"
        self.services = ["Paint Correction", "Ceramic Coating", "Interior Detailing", "Wash & Wax"]
        
        # Create output directory
        self.output_dir = Path("C:/Users/cjay4/OneDrive/Desktop/sincor-clean/clinton_videos")
        self.output_dir.mkdir(exist_ok=True)
        
        self.video_specs = {
            "business_intro": {
                "duration": 90,
                "title": "Clinton Auto Detailing - Business Introduction",
                "filename": "1_business_introduction.mp4",
                "script": self.get_business_intro_script()
            },
            "service_showcase": {
                "duration": 60,
                "title": "Clinton Auto Detailing - Service Showcase",
                "filename": "2_service_showcase.mp4",
                "script": self.get_service_showcase_script()
            },
            "customer_testimonial": {
                "duration": 45,
                "title": "Clinton Auto Detailing - Customer Testimonial",
                "filename": "3_customer_testimonial.mp4",
                "script": self.get_testimonial_script()
            },
            "before_after": {
                "duration": 30,
                "title": "Clinton Auto Detailing - Before & After",
                "filename": "4_before_after_transformation.mp4",
                "script": self.get_before_after_script()
            },
            "behind_scenes": {
                "duration": 60,
                "title": "Clinton Auto Detailing - Behind the Scenes",
                "filename": "5_behind_scenes_process.mp4",
                "script": self.get_behind_scenes_script()
            },
            "call_to_action": {
                "duration": 30,
                "title": "Clinton Auto Detailing - Call to Action",
                "filename": "6_call_to_action.mp4",
                "script": self.get_cta_script()
            }
        }

    def get_business_intro_script(self):
        return f"""Welcome to {self.business_name}, your premier auto detailing service in {self.location}.

For over a decade, we've been transforming vehicles with our professional detailing services. Our team specializes in paint correction, ceramic coating, interior detailing, and complete wash and wax services.

At {self.business_name}, we don't just clean your car, we restore its beauty and protect your investment. Every vehicle receives our signature attention to detail, using only premium products and proven techniques.

Whether you drive a luxury sedan, family S U V, or classic car, our experienced technicians treat every vehicle like it's our own. We take pride in delivering results that exceed your expectations.

Ready to experience the {self.business_name} difference? Call us today at {self.phone} to schedule your appointment. Your car deserves the best, and that's exactly what we deliver, every single time.

{self.business_name}, where excellence meets your expectations."""

    def get_service_showcase_script(self):
        return f"""Discover the complete range of premium services at {self.business_name}.

Paint Correction: Our certified technicians remove swirl marks, scratches, and oxidation, restoring your vehicle's paint to showroom condition.

Ceramic Coating: Protect your investment with our professional-grade ceramic coating. Long-lasting protection against U V rays, chemicals, and environmental contaminants.

Interior Detailing: From leather conditioning to carpet deep cleaning, we revitalize every surface inside your vehicle with meticulous care.

Wash and Wax: Our signature service combines thorough exterior cleaning with premium wax protection, leaving your car with an incredible shine.

Every service is performed by trained professionals using top-tier products and equipment. We guarantee satisfaction with every detail.

Experience the difference professional detailing makes. Call {self.phone} today. {self.business_name}, premium care for your vehicle."""

    def get_testimonial_script(self):
        return f"""I've been taking my cars to {self.business_name} for three years now, and they never disappoint. The team is professional, thorough, and truly cares about the quality of their work.

My B M W was looking tired after years of daily driving. The paint correction service they provided was incredible, it looks better than when I bought it new. The attention to detail is unmatched.

What sets {self.business_name} apart is their commitment to customer satisfaction. They explain every step of the process and always deliver on their promises.

The ceramic coating has been worth every penny. Six months later, my car still looks amazing and cleaning is so much easier. I recommend {self.business_name} to everyone I know.

If you want the best auto detailing in {self.location}, there's only one choice. Call {self.phone} and experience the difference for yourself.

Satisfied Customer, {self.business_name}."""

    def get_before_after_script(self):
        return f"""This is the power of professional detailing at {self.business_name}.

Before: Oxidized paint, swirl marks, and years of neglect. This vehicle had lost its original beauty.

After: Complete transformation through our paint correction and ceramic coating process. The results speak for themselves.

Our systematic approach removes imperfections while protecting your vehicle for the future. Every scratch tells a story, but it doesn't have to be permanent.

See what {self.business_name} can do for your vehicle. Call {self.phone} to schedule your transformation today.

{self.business_name}, bringing your car back to life."""

    def get_behind_scenes_script(self):
        return f"""Go behind the scenes at {self.business_name} and discover our meticulous process.

Step 1: Thorough inspection and documentation. We assess every detail before we begin.

Step 2: Safe washing using the two-bucket method and premium microfiber towels. Protecting your paint starts with proper technique.

Step 3: Clay bar treatment removes bonded contaminants that washing can't eliminate.

Step 4: Paint correction using professional-grade compounds and polishes. Our certified technicians have years of experience perfecting this art.

Step 5: Protection application, whether ceramic coating, sealant, or premium wax. We use only the finest products for long-lasting results.

Quality takes time, and we never rush the process. Every step is performed with precision because your vehicle deserves nothing less than perfection.

Experience the {self.business_name} difference. Call {self.phone} today."""

    def get_cta_script(self):
        return f"""Don't let another day pass with a vehicle that doesn't reflect your standards.

{self.business_name} is ready to transform your car with our premium detailing services. Paint correction, ceramic coating, interior detailing, we do it all.

Call NOW at {self.phone} to schedule your appointment. Our calendar fills up fast, so don't wait.

Located in {self.location}, we're your local experts in automotive perfection.

{self.business_name}. Call today, drive away amazed. {self.phone}."""

    def create_background_image(self, width=1920, height=1080, color=(25, 25, 112)):
        """Create a professional blue gradient background"""
        img = Image.new('RGB', (width, height), color)
        draw = ImageDraw.Draw(img)
        
        # Create gradient effect
        for y in range(height):
            shade = int(255 * (y / height * 0.3))
            color_grad = (min(255, color[0] + shade), min(255, color[1] + shade), min(255, color[2] + shade))
            draw.line([(0, y), (width, y)], fill=color_grad)
        
        # Add business name
        try:
            font = ImageFont.truetype("arial.ttf", 80)
        except:
            font = ImageFont.load_default()
        
        text = "CLINTON AUTO DETAILING"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), text, font=font, fill=(255, 255, 255))
        
        return np.array(img)

    def create_text_to_speech(self, text, filename):
        """Convert text to speech using gTTS"""
        try:
            tts = gTTS(text=text, lang='en', slow=False)
            temp_path = self.output_dir / f"temp_{filename}.mp3"
            tts.save(str(temp_path))
            return str(temp_path)
        except Exception as e:
            print(f"Error creating TTS for {filename}: {e}")
            return None

    def create_single_video(self, video_key):
        """Create a single video with background and voiceover"""
        video_info = self.video_specs[video_key]
        print(f"Creating: {video_info['title']}")
        
        try:
            # Create text-to-speech audio
            audio_file = self.create_text_to_speech(video_info['script'], video_key)
            if not audio_file:
                print(f"Failed to create audio for {video_key}")
                return False
            
            # Load audio to get duration
            audio_clip = AudioFileClip(audio_file)
            actual_duration = audio_clip.duration
            
            # Create background image
            bg_image = self.create_background_image()
            
            # Create video clip from background
            video_clip = ImageClip(bg_image, duration=actual_duration)
            
            # Add text overlay
            title_text = TextClip(self.business_name, 
                                fontsize=60, 
                                color='white', 
                                font='Arial-Bold',
                                size=(1920, None))
            title_text = title_text.set_position(('center', 100)).set_duration(actual_duration)
            
            phone_text = TextClip(self.phone, 
                                fontsize=40, 
                                color='yellow', 
                                font='Arial',
                                size=(1920, None))
            phone_text = phone_text.set_position(('center', 950)).set_duration(actual_duration)
            
            location_text = TextClip(f"Located in {self.location}", 
                                   fontsize=30, 
                                   color='white', 
                                   font='Arial',
                                   size=(1920, None))
            location_text = location_text.set_position(('center', 200)).set_duration(actual_duration)
            
            # Combine video with text overlays
            final_video = CompositeVideoClip([video_clip, title_text, phone_text, location_text])
            
            # Add audio
            final_video = final_video.set_audio(audio_clip)
            
            # Export video
            output_path = self.output_dir / video_info['filename']
            print(f"Rendering video to: {output_path}")
            
            final_video.write_videofile(
                str(output_path),
                fps=24,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            # Clean up
            audio_clip.close()
            final_video.close()
            
            # Remove temp audio file
            if os.path.exists(audio_file):
                os.remove(audio_file)
            
            print(f"[SUCCESS] Successfully created: {video_info['filename']}")
            return True
            
        except Exception as e:
            print(f"Error creating video {video_key}: {e}")
            return False

    def create_all_videos(self):
        """Create all 6 videos"""
        print("=" * 60)
        print("CREATING CLINTON AUTO DETAILING MP4 VIDEOS")
        print("=" * 60)
        
        successful = 0
        total = len(self.video_specs)
        
        for video_key in self.video_specs.keys():
            if self.create_single_video(video_key):
                successful += 1
            print()  # Empty line for readability
        
        print("=" * 60)
        print(f"COMPLETED: {successful}/{total} videos created successfully")
        print(f"Output directory: {self.output_dir}")
        print("=" * 60)
        
        # List created files
        if successful > 0:
            print("\nCreated video files:")
            for file in self.output_dir.glob("*.mp4"):
                size = file.stat().st_size / (1024 * 1024)  # Convert to MB
                print(f"  - {file.name} ({size:.1f} MB)")

def main():
    """Main execution function"""
    print("Starting Clinton Auto Detailing Video Generation...")
    print("This will create actual MP4 files using free tools.")
    
    generator = ClintonVideoGeneratorFree()
    generator.create_all_videos()
    
    return generator

if __name__ == "__main__":
    generator = main()