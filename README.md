# TNxIDM v1.1

## English

TNxIDM is an original, lightweight download manager for Windows 10/11.
Segmented multi-connection downloads, pause/resume, queue, scheduling,
site grabber (direct links only), system tray and a Liquid Glass UI.

### First run (Windows)
1. Unzip `TNxIDM-PC-Windows-v1.1.zip` to a folder.
2. Keep `TNxIDM.exe` inside its folder — do not move it out alone, or
   its bundled libraries will be missing.
3. Double-click `TNxIDM.exe`.
4. Windows SmartScreen may show an unknown-publisher warning because the
   exe is unsigned: click **More info**, then **Run anyway**.
5. Default downloads go to `Downloads/TNxIDM/<Category>`.

### Self-test
```
TNxIDM.exe --self-test
```
It starts a local Range server, downloads with 8 segments, pauses,
resumes, and checks the SHA-256 checksum. It prints PASS on success.


### Browser extension (v1.1+, Chrome/Edge)
The release zip contains a `browser-extension` folder.
1. Install and start TNxIDM (the Setup.exe installer is the easy way).
2. In Chrome/Edge open `chrome://extensions`, turn on **Developer mode**.
3. Click **Load unpacked** and select the `browser-extension` folder.
4. Click the TNxIDM icon in the toolbar, then **Test connection** — it should
   say "Connected to TNxIDM".
5. Downloads of common file types are now taken over by TNxIDM automatically.
   Right-click any link > **Download with TNxIDM** to send one link manually.

### Honest limits in v1.1
- Direct file links only — YouTube/streaming video downloading is not supported.
- The browser extension (v1.1) takes over downloads in Chrome/Edge and sends
  them to TNxIDM automatically; TNxIDM must be running (tray is fine).
  Firefox is untested with the extension.
- A server that does not support HTTP Range falls back to a single
  connection; pausing such a download restarts that file on resume,
  because the server cannot resume it. Segmented downloads resume
  from their saved offsets and never restart from zero.
- Real-time Apple-style light refraction is not possible in Qt; the UI
  is the closest frosted-glass approximation (RGBA fills, shadows, gradients).

## বাংলা

TNxIDM Windows 10/11-এর জন্য একটি আসল, হালকা ডাউনলোড ম্যানেজার।
মাল্টি-কানেকশন ডাউনলোড, বিরতি/আবার শুরু, সারি, সময়সূচি, গ্র্যাবার
(শুধুমাত্র সরাসরি লিঙ্ক) এবং Liquid Glass UI রয়েছে।

### প্রথমবার চালানো (Windows)
1. `TNxIDM-PC-Windows-v1.1.zip` একটি ফোল্ডারে আনজিপ করুন।
2. `TNxIDM.exe` তার ফোল্ডারের ভেতরেই রাখুন — একা সরাবেন না, তা না হলে
   প্রয়োজনীয় লাইব্রেরি পাওয়া যাবে না।
3. `TNxIDM.exe`-এ ডাবল-ক্লিক করুন।
4. exe স্বাক্ষরিত নয় বলে Windows SmartScreen অজানা প্রকাশকের সতর্কতা
   দেখাতে পারে: **More info**, তারপর **Run anyway** ক্লিক করুন।
5. ডিফল্ট ডাউনলোড `Downloads/TNxIDM/<Category>` ফোল্ডারে যাবে।

### সেলফ-টেস্ট
```
TNxIDM.exe --self-test
```
এটি লোকাল Range সার্ভার চালু করে, 8টি সেগমেন্টে ডাউনলোড করে, মাঝপথে
বিরতি দেয়, আবার শুরু করে এবং SHA-256 যাচাই করে। সফল হলে PASS দেখাবে।

### ব্রাউজার এক্সটেনশন (v1.1+, Chrome/Edge)
রিলিজ জিপে `browser-extension` ফোল্ডার আছে।
1. TNxIDM ইনস্টল করে চালু করুন (Setup.exe দিয়ে সহজ)।
2. Chrome/Edge-এ `chrome://extensions` খুলে **Developer mode** চালু করুন।
3. **Load unpacked** ক্লিক করে `browser-extension` ফোল্ডার সিলেক্ট করুন।
4. টুলবারে TNxIDM আইকনে ক্লিক করে **Test connection** চাপুন — "Connected to
   TNxIDM" দেখাবে।
5. এখন সাধারণ ফাইল টাইপের ডাউনলোড স্বয়ংক্রিয়ভাবে TNxIDM নিয়ে নেবে।
   যেকোনো লিঙ্কে রাইট-ক্লিক > **Download with TNxIDM** দিলে একটি লিঙ্ক
   ম্যানুয়ালি পাঠানো যাবে।
