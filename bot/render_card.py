from PIL import Image, ImageDraw, ImageFont
W,H=1080,1350
img=Image.new('RGB',(W,H),(9,45,39)); d=ImageDraw.Draw(img)
d.rounded_rectangle((28,28,W-28,H-28),radius=28,outline=(205,168,88),width=5)
d.rounded_rectangle((52,52,W-52,H-52),radius=20,outline=(112,153,116),width=2)
ft=ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoKufiArabic-ExtraBold.ttf',52)
fs=ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoKufiArabic-Medium.ttf',32)
fb=ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf',34)
fn=ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf',26)
def rtl(t,font,xy,fill,anchor='ra'):
    d.text(xy,t,font=font,fill=fill,anchor=anchor,direction='rtl',language='ar')
def lines(t,n):
    out=[];cur=''
    for w in t.split():
        if len(cur)+len(w)+1<=n:cur=(cur+' '+w).strip()
        else:out.append(cur);cur=w
    if cur:out.append(cur)
    return out
rtl('سبيل الرشاد',ft,(W//2,125),(231,202,126),'ma');rtl('آية وتفسير',fs,(W//2,200),(166,205,172),'ma');d.line((150,245,W-150,245),fill=(205,168,88),width=3)
verse='وَلَوْ شِئْنَا لَرَفَعْنَاهُ بِهَا وَلَٰكِنَّهُ أَخْلَدَ إِلَى الْأَرْضِ وَاتَّبَعَ هَوَاهُ ۚ فَمَثَلُهُ كَمَثَلِ الْكَلْبِ إِن تَحْمِلْ عَلَيْهِ يَلْهَثْ أَوْ تَتْرُكْهُ يَلْهَث ۚ ذَٰلِكَ مَثَلُ الْقَوْمِ الَّذِينَ كَذَّبُوا بِآيَاتِنَا ۚ فَاقْصُصِ الْقَصَصَ لَعَلَّهُمْ يَتَفَكَّرُونَ رقم الآية: 176'
y=315
for line in lines(verse,34):rtl(line,fb,(W-105,y),(250,246,227));y+=54
d.line((150,y+20,W-150,y+20),fill=(112,153,116),width=2);y+=85;rtl('تفسير السعدي',fs,(W-105,y),(231,202,126));y+=65
ex='وَلَوْ شِئْنَا لَرَفَعْنَاهُ بِهَا بأن نوفقه للعمل بها، فيرتفع في الدنيا والآخرة، فَأَخْلَدَ إِلَى الأرْضِ وَاتَّبَعَ هَوَاهُ.'
for line in lines(ex,42):rtl(line,fn,(W-105,y),(232,238,224));y+=40
rtl('سورة الأعراف، الآية 176',fn,(W//2,H-95),(166,205,172),'ma');img.save('/home/ubuntu/quran_card.png',quality=95)
