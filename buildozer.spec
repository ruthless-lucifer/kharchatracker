[app]

# (str) Title of your application
title = Kharcha Track

# (str) Package name
package.name = kharchatrack

# (str) Package domain (needed for android/ios packaging)
package.domain = org.kharcha

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let everything relevant in, exclusions below)
source.include_exts = py,kv,json,png

# (list) Patterns to ignore
source.exclude_globs = .git/*, .github/*, bin/*, build/*, tools/*, *.log, screenshot*.png, README.md, buildozer.spec.local

# (str) Application versioning
version = 1.0

# (list) Application requirements (python-for-android recipes)
requirements = python3,kivy

# (str) Orientation of the app
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Android permissions (the app is fully offline, none needed)
android.permissions =

# (str) Icon for the application
icon.icon = assets/icon.png

# (str) Splash / loading screen image
presplash.presplash = assets/presplash.png

# (list) Android architectures of the build. arm64-v8a covers essentially
# every phone released in recent years and builds in about half the time.
android.archs = arm64-v8a

# (int) Android API to use. Recent API gives a bigger app but better
# platform support. Buildozer will download the SDK if needed.
android.api = 34

# (int) Minimum API level required on the device
android.minapi = 21

# (bool) Targets a debug build (debuggable, installable). Use 'release'
# via `buildozer android release` for the Play Store.
android.debug = 1

# (bool) Keep the app and its data when you re-install over a previous apk
android.keep_private_data = False

[buildozer]

# (int) Log level (0 = error, 1 = info, 2 = debug)
log_level = 2

# (int) Maximum number of concurrent jobs during the build
max_jobs = 4