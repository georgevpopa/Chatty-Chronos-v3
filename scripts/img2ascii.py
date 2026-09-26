from PIL import Image, ImageEnhance

def image_to_ascii(image_path, width=130):
    # Standard 11-character ramp from darkest to lightest
    ascii_chars = [" ", ".", ",", ":", ";", "+", "*", "?", "%", "S", "#", "@"]
    
    img = Image.open(image_path)
    
    # 0. Crop the center of the image to focus on the face/hourglass
    w, h = img.size
    left = int(w * 0.25)
    right = int(w * 0.75)
    top = int(h * 0.15)
    bottom = int(h * 0.85)
    img = img.crop((left, top, right, bottom))
    
    # 1. Enhance contrast to make the figure pop from the background
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)  # Boost contrast heavier
    
    # 2. Resize maintaining terminal font aspect ratio (~0.45 or 0.5)
    w, h = img.size
    aspect_ratio = h / float(w)
    height = int(aspect_ratio * width * 0.45)
    img = img.resize((width, height))
    
    # 3. Grayscale
    img = img.convert('L')
    pixels = list(img.getdata())
    
    # 4. Map to ASCII
    # Darker pixels (near 0) map to space, lighter (near 255) map to @
    ascii_str = ""
    for pixel in pixels:
        # threshold the absolute black background
        if pixel < 20:
            ascii_str += " "
        else:
            idx = int((pixel / 255.0) * (len(ascii_chars) - 1))
            ascii_str += ascii_chars[idx]
            
    # 5. Split into lines
    ascii_img = ""
    for i in range(0, len(ascii_str), width):
        ascii_img += ascii_str[i:i+width] + "\n"
        
    import os
    output_path = os.path.join(os.path.dirname(__file__), "ascii_art.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ascii_img)
        
    print(f"ASCII art saved to {output_path}")

image_to_ascii(r"C:\Users\georg\Downloads\Gemini_Generated_Image_v218lbv218lbv218.png", width=130)
