import os
import glob

def remove_video_nav():
    files = glob.glob('/Users/ahmed/abrag/dashboard-admin/*.html')
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        skip_next = False
        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue
            if '<a href="videos.html"' in line:
                # If it's split across lines
                if '<span' in line and '</span>' not in line:
                    skip_next = True
                continue
            new_lines.append(line)
            
        with open(file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

remove_video_nav()
