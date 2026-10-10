# Kharcha Track

A small, offline expense tracker built with **Python + Kivy**. "Kharcha"
means *expense* in Hindi - every rupee you spend, tracked in one place.

## Features

- Add expense: amount, category (Food, Transport, Shopping, Bills, Health,
  Fun, Other), optional note, and date (defaults to today).
- Monthly summary card: total spent, number of expenses, top category,
  plus a category breakdown bar.
- Month navigation (previous / next / jump to today) and category filter chips.
- Tap any entry to edit it; delete with the `X` button (with confirmation).
- All data is stored locally in a JSON file in the app's private folder -
  **no internet, no account, 100% offline**.
- Indian style number grouping (`₹12,34,567`) and Indian Rupee symbol.
  Change `CURRENCY` in `main.py` for a different currency.

## Run on your computer

```bash
python -m pip install -r requirements.txt
python main.py
```

- `python main.py --smoke` boots the UI, runs automated checks of the
  add / edit / delete / month / storage logic, and exits.
- `python main.py --shot` renders a screenshot with demo data to
  `screenshot0001.png` (dev helper).

## Get the Android APK

Buildozer (the Android packager) only runs on **Linux**, so from Windows you
have two easy options.

### Option 1 - GitHub Actions (simplest, no Linux needed)

1. Push this folder to a GitHub repository.
2. In the repo: **Actions > Build Android APK > Run workflow**.
3. When it finishes, download the `kharcha-track-apk` artifact - the
   `*.apk` inside is ready to install on your phone.

### Option 2 - Buildozer on WSL / Ubuntu

```bash
# inside a Linux machine or WSL2 (Ubuntu 22.04/24.04)
sudo apt-get update
sudo apt-get install -y git zip unzip openjdk-17-jdk autoconf libtool \
    pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 \
    cmake libffi-dev libssl-dev
python3 -m pip install --user buildozer

cd kharcha-track
buildozer -v android debug
```

The APK appears in `bin/`. Transfer it to your phone and install it
(allow "install from unknown sources" on first install).

> First build downloads the Android SDK/NDK and takes a while - this is
> normal and only happens once.

## Project layout

```
main.py              App: screens, storage, add/edit/delete, summary logic
kharcha.kv           Kivy UI layout (look & feel)
buildozer.spec       Buildozer config used to create the APK
assets/
  icon.png           Launcher icon
  presplash.png      Loading screen
tools/make_icons.py  Regenerates the icon images (Pillow)
.github/workflows/   GitHub Actions workflow that builds the APK
```

## Ideas to extend

- Add a monthly budget and overspending alert.
- Charts per category (PieChart) - kivy-garden's graph.
- Import/export CSV backup.
- Reminder notification to log daily expenses (needs `plyer`)."# kharchatracker" 
