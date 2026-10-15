"""Assemble recorded browser frames into a captioned frontend walkthrough."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parent
data = json.loads((root / 'capture-manifest.json').read_text(encoding='utf-8'))
frames = data['frames']
fps = 2
duration = len(frames) / fps
# Keep the final title for each frame; early setup markers share one frame.
by_frame = {item['frame']: item for item in data['chapters']}
chapters = sorted(by_frame.values(), key=lambda item: item['frame'])
chapters = [item for item in chapters if item['frame'] > 0]
chapters[0]['frame'] = 0

def ass_time(seconds):
    centiseconds = round(seconds * 100)
    return f'{centiseconds // 360000}:{centiseconds // 6000 % 60:02}:{centiseconds // 100 % 60:02}.{centiseconds % 100:02}'

def clock(seconds):
    return f'{int(seconds) // 60:02}:{int(seconds) % 60:02}'

def escape(text):
    return text.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')

ass = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 816
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Arial,24,&H008AD1FF,&H008AD1FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,28,28,15,1
Style: Description,Arial,18,&H00E7E0D8,&H00E7E0D8,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,28,28,51,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
metadata = ';FFMETADATA1\ntitle=AI Guard - Frontend Feature Walkthrough\ncomment=Real frontend interactions; synthetic demo data; offline demonstration model.\n'
guide = ['# AI Guard frontend demo', '', f'Runtime: {clock(duration)}. Captioned walkthrough of the running frontend; no voiceover.', '', '## Chapters', '']
for index, chapter in enumerate(chapters):
    start = chapter['frame'] / fps
    end = chapters[index + 1]['frame'] / fps if index + 1 < len(chapters) else duration
    ass += f'Dialogue: 0,{ass_time(start)},{ass_time(end)},Title,,0,0,0,,{escape(chapter["title"])}\n'
    ass += f'Dialogue: 0,{ass_time(start)},{ass_time(end)},Description,,0,0,0,,{escape(chapter["description"])}\n'
    metadata += f'\n[CHAPTER]\nTIMEBASE=1/1000\nSTART={int(start * 1000)}\nEND={int(end * 1000)}\ntitle={chapter["title"]}\n'
    guide.append(f'- {clock(start)} — {chapter["title"].split(" | ")[-1]}: {chapter["description"]}')

guide += ['', '## Recording notes', '',
          '- Uses the existing deterministic offline model; no hosted model was configured.',
          '- Evaluation metrics shown are from the existing 46-case synthetic report, not real-world accuracy claims.',
          '- The document creation form was demonstrated by saving a public synthetic checklist: Video demo - Safe AI checklist (DOC-56eff00241).',
          '- Demo chat requests created normal audit events. The synthetic confidential request was rejected in the review queue.',
          '- Existing policy values were saved without modification. No application source code was changed for this recording.',
          '- Editing access and uploading a text file are visible in the document form; they were not executed in this walkthrough.',
          '- Approval execution is available in the product; the recorded review demonstrates rejection instead.', '']
(root / 'captions.ass').write_text(ass, encoding='utf-8')
(root / 'chapters.ffmetadata').write_text(metadata, encoding='utf-8')
(root.parent / 'AI-Guard-Frontend-Demo-Chapters.md').write_text('\n'.join(guide), encoding='utf-8')

samples = [min(len(frames) - 1, int((i + .5) * len(frames) / 12)) for i in range(12)]
sheet = Image.new('RGB', (1600, 780), '#100b07')
draw = ImageDraw.Draw(sheet)
for tile, frame_index in enumerate(samples):
    image = Image.open(frames[frame_index]['file']).convert('RGB')
    image.thumbnail((400, 225))
    x, y = (tile % 4) * 400, (tile // 4) * 260
    sheet.paste(image, (x, y))
    draw.text((x + 8, y + 230), f'{clock(frame_index / fps)} | Frame {frame_index}', fill='#ffd18a')
sheet.save(root / 'quality-check.jpg', quality=90)
print(f'{len(frames)} frames; {len(chapters)} chapters; {duration:.1f} seconds')
