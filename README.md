# TNxIDM v1.0

## English

TNxIDM is an original, lightweight download manager for Windows 10/11.
Segmented multi-connection downloads, pause/resume, queue, scheduling,
site grabber (direct links only), system tray and a Liquid Glass UI.

### First run (Windows)
1. Unzip `TNxIDM-PC-Windows-v1.0.zip` to a folder.
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

### Honest limits in v1.0
- Direct file links only — YouTube/streaming video downloading is not supported.
- Full in-browser download interception requires a browser extension and
  is not included in v1.0; clipboard monitoring is the v1.0 integration.
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
1. `TNxIDM-PC-Windows-v1.0.zip` একটি ফোল্ডারে আনজিপ করুন।
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
