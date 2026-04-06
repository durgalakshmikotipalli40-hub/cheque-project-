import os
import glob

css = """
/* Responsive Media Queries */
@media (max-width: 768px) {
    .navbar { flex-direction: column; padding: 15px; text-align: center; }
    .navbar ul { flex-wrap: wrap; justify-content: center; margin-top: 10px; gap: 10px; padding: 0; }
    .navbar ul li a { padding: 8px 10px; font-size: 0.9rem; }
    .container, .auth-container, .login-container { 
        margin: 20px auto !important; 
        padding: 20px !important; 
        width: 95% !important; 
        max-width: 100% !important; 
        border-radius: 15px !important; 
    }
    .content { padding: 20px !important; }
    .glass-card { padding: 20px !important; }
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.3rem !important; }
    .navbar-brand { font-size: 1.4rem !important; }
    table { font-size: 0.8rem; overflow-x: auto; display: block; }
    th, td { padding: 6px; }
    .upload-box { padding: 15px; }
    .toast-container { width: 90%; left: 5%; right: 5%; top: 10px; }
    img.preview-img { border-width: 2px; }
}
"""

template_dir = r"c:\Users\durga\Desktop\chequeprojet AI\chequeprojet\templates"
for filepath in glob.glob(os.path.join(template_dir, "*.html")):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        if "/* Responsive Media Queries */" not in content and "</style>" in content:
            content = content.replace("</style>", css + "\n</style>")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Patched {os.path.basename(filepath)}")
    except Exception as e:
         print(f"Error patching {os.path.basename(filepath)}: {e}")
