"""Review-only local copper visual; coordinates in millimetres, not fabrication art."""
from pathlib import Path
import json, colorsys
from PIL import Image, ImageDraw, ImageFont
out=Path(__file__).resolve().parent
data=json.loads((out/'local_geometry.json').read_text())
scale=90; size=1260; origin=(84,61)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
def xy(p):return ((p[0]-origin[0])*scale,(p[1]-origin[1])*scale)
nets=sorted(set(i['net'] for i in data['items']))
colors={n:tuple(int(c*255) for c in colorsys.hsv_to_rgb(j/len(nets),.8,.65)) for j,n in enumerate(nets)}
colors['GND']=(20,110,20)
for layer in range(2):
    im=Image.new('RGB',(size,size),'white');d=ImageDraw.Draw(im)
    for v in range(84,99):d.line((xy((v,61)),xy((v,75))),fill='#dddddd');d.text(xy((v,61)),str(v),font=font,fill='black')
    for v in range(61,76):d.line((xy((84,v)),xy((98,v))),fill='#dddddd');d.text(xy((84,v)),str(v),font=font,fill='black')
    for n in data['island']['nodes']:
        if n['layer']==['F.Cu','B.Cu'][layer]:d.polygon([xy(p) for p in n['outline_mm']],fill='#d2efd2')
    for item in data['items']:
        if layer not in item['layers']:continue
        color=colors[item['net']]
        if item['class']=='PCB_TRACK':
            d.line([xy(item['start']),xy(item['end'])],fill=color,width=max(1,round(item['width']*scale)))
        elif item['class']=='PCB_VIA':
            x,y=xy(item['pos']);r=item['width']*scale/2
            d.ellipse((x-r,y-r,x+r,y+r),fill=color);r=item['drill']*scale/2;d.ellipse((x-r,y-r,x+r,y+r),fill='white')
        elif item['class']=='PAD':
            x,y=xy(item['pos']);w,h=item['size'];
            if round(item['angle'])%180==90:w,h=h,w
            w*=scale/2;h*=scale/2;d.rectangle((x-w,y-h,x+w,y+h),fill=color)
            if item['ref']=='U1':d.text((x-w,y-h),item['pad'],font=font,fill='black')
    d.text((30,1200),['F.Cu','B.Cu'][layer]+' — green polygon: isolated U1.12 copper; coordinates mm',font=font,fill='black')
    im.save(out/('local_'+str(layer)+'.png'))
