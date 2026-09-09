# TANK funksional bloklari

## 1. Kamera va sektor bloki

Powered USB hub orqali ulangan UVC kameralar Ubuntu/VMware ichida `/dev/video*`
sifatida ko‘rinadi. Har bir kamera bitta sektor bilan bog‘lanadi; kamera IP
manzil olmaydi.

## 2. AI aniqlash bloki

Ubuntu kadrni ONNX/YOLO modelga beradi, obyekt sinfi, confidence, bounding box va
track holatini hisoblaydi. Track kamida `confirmationFrames` davomida ko‘rinsa,
dron tasdiqlangan hisoblanadi.

## 3. Masofa-xavf bloki

TF02-Pro o‘lchovi sektor bo‘yicha median + EMA filtridan o‘tadi. Noto‘g‘ri yoki
keskin sakragan o‘lchov rad etiladi. `nearEnterMeters` chegarasiga ketma-ket
`nearEnterSamples` marta kirilganda xavfli zona yoqiladi; `nearExitMeters` dan
ketma-ket `nearExitSamples` marta chiqilganda o‘chadi. Kirish va chiqish
chegaralarining farqi (hysteresis) miltillashni kamaytiradi.

## 4. Indikator va aktuator bloki

Server sektor qarorini JSON-Lines orqali ESP32-S3 ga yuboradi: `OFF`, `WHITE`
yoki `RED`. ESP32 mos GPIO juftligini boshqaradi va buyruq 2 soniya yo‘qolsa
`OFF` holatiga qaytadi. Kuchli lampa, rele yoki sirena uchun alohida driver va
quvvat manbai kerak; GPIO bevosita yukni quvvatlamaydi.

## 5. Operator bloki

Flutter ilovasi telefon, Android/iOS qurilma yoki macOS noutbukda ishlaydi.
Server manzili runtime’da kiritiladi, preview va WebSocket qayta ulanadi.

## 6. Brauzer monitoring bloki

Server ishga tushgach, istalgan tarmoqdagi brauzerda
`http://SERVER_IP:8080/` ochiladi. Sahifa kameralar preview’i, kamera FPS/ulanish
holati, server health va oxirgi WebSocket hodisalarini ko‘rsatadi. Bu Flutter’dan
mustaqil kuzatuv oynasidir.
