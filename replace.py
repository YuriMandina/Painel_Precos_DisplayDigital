import os, glob

for f in glob.glob('painel/templates/**/*.html', recursive=True):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
        
    if '<script src="https://cdn.tailwindcss.com"></script>' in content:
        new_content = content.replace(
            '<script src="https://cdn.tailwindcss.com"></script>', 
            '{% load tailwind_cli %}\n    {% tailwind_css %}'
        )
        with open(f, 'w', encoding='utf-8') as file:
            file.write(new_content)
        print(f"Replaced in {f}")
