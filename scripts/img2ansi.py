from PIL import Image

def image_to_ansi(image_path, new_width=60):
    img = Image.open(image_path)
    img = img.convert('RGB')
    
    # Calculate height. We use 2 spaces per pixel horizontally to make it roughly square
    width, height = img.size
    aspect_ratio = height / width
    new_height = int((new_width / 2) * aspect_ratio)
    
    # Resize the image down
    img = img.resize((new_width // 2, new_height))
    pixels = img.load()
    
    output = []
    # Loop over rows
    for y in range(new_height):
        row_str = ""
        for x in range(new_width // 2):
            r, g, b = pixels[x, y]
            # Use Rich markup for background color with two spaces
            row_str += f"[on rgb({r},{g},{b})]  [/]"
        output.append(row_str)
        
    return "\n".join(output)

import os
output_path = os.path.join(os.path.dirname(__file__), "ansi_out.txt")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(image_to_ansi(r"C:\Users\georg\Downloads\Gemini_Generated_Image_v218lbv218lbv218.png", new_width=100))
