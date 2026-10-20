"""Повеќејазичност (i18n): сите текстови во играта на едно место.

Јазици: македонски, англиски, албански, турски, јазиците што најчесто се
зборуваат во Македонија. Нов јазик се додава со уште еден речник во STRINGS
и еден ред во LANGUAGES, без менување на останатиот код.

Правила (од UX препораките):
  - името на јазикот секогаш е на самиот тој јазик (Shqip, не „албански“),
  - без знамиња: знамињата претставуваат држави, не јазици,
  - јазикот на системот се препознава автоматски и се предлага прв.
"""

import json
import locale
from pathlib import Path

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "user_settings.json"

# (код, име на самиот јазик, кратенка)
LANGUAGES = [
    ("mk", "Македонски", "МК"),
    ("en", "English", "EN"),
    ("sq", "Shqip", "SQ"),
    ("tr", "Türkçe", "TR"),
]

STRINGS = {
    # ------------------------------------------------------------------ МК
    "mk": {
        "title": "ЕХО",
        "lang_title": "Избери јазик",
        "lang_welcome": "Добредојде",
        "lang_detected": "препознаен од системот",
        "lang_hint": "Enter  отвори го посочениот   ·   ← →  или глувче  насочи",
        "tagline": "Звукот ти е очи. И предавник.",
        "menu_play": "Играј",
        "menu_howto": "Упатство",
        "menu_language": "Јазик",
        "menu_sound_on": "Звук: вклучен",
        "menu_sound_off": "Звук: исклучен",
        "menu_quit": "Излез",
        "menu_level": "Ниво {n} · {name}",
        "hint_nav": "↑ ↓  избор   ·   ← →  ниво   ·   Enter  потврди",
        "hint_back": "Esc  назад",
        "level_label": "НИВО {n}",
        "level_1": "Тишина",
        "level_2": "Шепоти",
        "level_3": "Ловиште",
        "hud_stones": "камчиња",
        "hud_clap": "плескање",
        "hud_pause": "Esc  пауза",
        "pause_title": "ПАУЗА",
        "pause_resume": "Продолжи",
        "pause_restart": "Почни одново",
        "pause_menu": "Главно мени",
        "win_title": "ИЗЛЕЗЕ",
        "win_time": "Време: {time}",
        "win_next": "Следно ниво",
        "win_all": "Ги помина сите нивоа.",
        "lose_title": "ТЕ ФАТИ",
        "lose_sub": "Те слушна.",
        "retry": "Обиди се пак",
        "howto_title": "Упатство",
        "howto_pages": "← →  страници   ·   Esc  назад",
        "p1_title": "Цел",
        "p1_text": "Заробен си во целосно темна пештера. Пронајди го излезот: зелениот сјај што пулсира. Ѕидовите не ги гледаш, ги откриваш само со звук.",
        "p2_title": "Звукот ти е очи",
        "p2_text": "Секој звук испушта бран што за момент ги осветлува ѕидовите. Чекорите прават мали бранови, плескањето голем. Камчето го осветлува местото каде паѓа. Но секој звук го слушаат и чудовиштата.",
        "p3_title": "Чудовиштата",
        "p3_text": "Слепи се, но слушаат одлично. Ги гледаш само кога ќе ги допре твој бран, а нивните чекори оставаат црвени бранови. Кога едно ќе те слушне, вреска и ги вика другите.",
        "p3_tip": "Совет: камче настрана ги одвлекува. Камче во чудовиште (E) го уништува, а промашување блиску го тера да бега. Срцето чука побрзо кога се блиску.",
        "ctl_move": "Движење",
        "ctl_move_arrows": "Движење (и со стрелки)",
        "ctl_sneak": "Шуњање (тивко)",
        "ctl_clap": "Плескање",
        "ctl_stone": "Камче кога стрелката покажува кон целта",
        "ctl_stone_aim": "Камче каде покажуваш",
        "state_flee": "Бега",
        "ctl_mute": "Звук вкл/искл",
        "ctl_pause": "Пауза",
        "ctl_debug": "Debug режим",
        "state_patrol": "Патрола",
        "state_investigate": "Истражува",
        "state_hunt": "Лови",
        "state_search": "Пребарува",
        "state_patrol_d": "шета бавно",
        "state_investigate_d": "оди кон звук",
        "state_hunt_d": "трча кон тебе",
        "state_search_d": "те бара наоколу",
        "p3_demo_hint": "↑ ↓  или клик: види и слушни ја секоја состојба",
        "debug_sounds": "звуци",
        "debug_monsters": "чудовишта",
        "intro_remember": "Се сеќаваат на тебе.",
        "debug_memory": "меморија (стара / нова)",
        "dir_title": "Директор",
        "dir_build": "градење",
        "dir_peak": "врв",
        "dir_relax": "одмор",
        "dir_tension": "напнатост",
        "dir_calm": "мир",
        "hint_pressure": "притисок",
        "hint_exit": "чува излез",
        "hint_relax": "одмор",
    },
    # ------------------------------------------------------------------ EN
    "en": {
        "title": "ECHO",
        "lang_title": "Choose language",
        "lang_welcome": "Welcome",
        "lang_detected": "detected from system",
        "lang_hint": "Enter  open the one pointed at   ·   ← →  or mouse  aim",
        "tagline": "Sound is your eyes. And your betrayer.",
        "menu_play": "Play",
        "menu_howto": "How to play",
        "menu_language": "Language",
        "menu_sound_on": "Sound: on",
        "menu_sound_off": "Sound: off",
        "menu_quit": "Quit",
        "menu_level": "Level {n} · {name}",
        "hint_nav": "↑ ↓  select   ·   ← →  level   ·   Enter  confirm",
        "hint_back": "Esc  back",
        "level_label": "LEVEL {n}",
        "level_1": "Silence",
        "level_2": "Whispers",
        "level_3": "Hunting Ground",
        "hud_stones": "stones",
        "hud_clap": "clap",
        "hud_pause": "Esc  pause",
        "pause_title": "PAUSED",
        "pause_resume": "Resume",
        "pause_restart": "Restart",
        "pause_menu": "Main menu",
        "win_title": "YOU ESCAPED",
        "win_time": "Time: {time}",
        "win_next": "Next level",
        "win_all": "You cleared every level.",
        "lose_title": "IT CAUGHT YOU",
        "lose_sub": "It heard you.",
        "retry": "Try again",
        "howto_title": "How to play",
        "howto_pages": "← →  pages   ·   Esc  back",
        "p1_title": "Goal",
        "p1_text": "You are trapped in a pitch-black cave. Find the exit: the pulsing green glow. You cannot see the walls; you discover them only through sound.",
        "p2_title": "Sound is your eyes",
        "p2_text": "Every sound sends out a wave that lights up the walls for a moment. Footsteps make small waves, a clap makes a big one. A stone lights up the spot where it lands. But the monsters hear every sound too.",
        "p3_title": "The monsters",
        "p3_text": "They are blind, but their hearing is excellent. You only see them when one of your waves touches them, and their footsteps leave red waves. When one hears you, it shrieks and calls the others.",
        "p3_tip": "Tip: a stone to the side distracts them. A stone that hits a monster (E) destroys it; a near miss makes it flee. Your heart beats faster when they are close.",
        "ctl_move": "Move",
        "ctl_move_arrows": "Move (arrows too)",
        "ctl_sneak": "Sneak (quiet)",
        "ctl_clap": "Clap",
        "ctl_stone": "Stone when the arrow points at it",
        "ctl_stone_aim": "Stone where you point",
        "state_flee": "Fleeing",
        "ctl_mute": "Sound on/off",
        "ctl_pause": "Pause",
        "ctl_debug": "Debug mode",
        "state_patrol": "Patrol",
        "state_investigate": "Investigate",
        "state_hunt": "Hunt",
        "state_search": "Search",
        "state_patrol_d": "wanders slowly",
        "state_investigate_d": "walks to a sound",
        "state_hunt_d": "runs at you",
        "state_search_d": "looks around for you",
        "p3_demo_hint": "↑ ↓  or click: see and hear each state",
        "debug_sounds": "sounds",
        "debug_monsters": "monsters",
        "intro_remember": "They remember you.",
        "debug_memory": "memory (old / new)",
        "dir_title": "Director",
        "dir_build": "build-up",
        "dir_peak": "peak",
        "dir_relax": "relax",
        "dir_tension": "tension",
        "dir_calm": "calm",
        "hint_pressure": "pressure",
        "hint_exit": "guard exit",
        "hint_relax": "relax",
    },
    # ------------------------------------------------------------------ SQ
    "sq": {
        "title": "JEHONA",
        "lang_title": "Zgjidh gjuhën",
        "lang_welcome": "Mirë se vini",
        "lang_detected": "zbuluar nga sistemi",
        "lang_hint": "Enter  hap të treguarin   ·   ← →  ose miu  drejto",
        "tagline": "Tingulli janë sytë e tu. Dhe tradhtari yt.",
        "menu_play": "Luaj",
        "menu_howto": "Udhëzime",
        "menu_language": "Gjuha",
        "menu_sound_on": "Zëri: aktiv",
        "menu_sound_off": "Zëri: joaktiv",
        "menu_quit": "Dil",
        "menu_level": "Niveli {n} · {name}",
        "hint_nav": "↑ ↓  zgjidh   ·   ← →  niveli   ·   Enter  konfirmo",
        "hint_back": "Esc  kthehu",
        "level_label": "NIVELI {n}",
        "level_1": "Heshtja",
        "level_2": "Pëshpëritjet",
        "level_3": "Vendi i gjuetisë",
        "hud_stones": "gurë",
        "hud_clap": "duartrokitje",
        "hud_pause": "Esc  pauzë",
        "pause_title": "PAUZË",
        "pause_resume": "Vazhdo",
        "pause_restart": "Fillo nga e para",
        "pause_menu": "Menyja kryesore",
        "win_title": "SHPËTOVE",
        "win_time": "Koha: {time}",
        "win_next": "Niveli tjetër",
        "win_all": "I kalove të gjitha nivelet.",
        "lose_title": "TË KAPI",
        "lose_sub": "Të dëgjoi.",
        "retry": "Provo përsëri",
        "howto_title": "Udhëzime",
        "howto_pages": "← →  faqet   ·   Esc  kthehu",
        "p1_title": "Qëllimi",
        "p1_text": "Je i bllokuar në një shpellë krejtësisht të errët. Gjej daljen: dritën e gjelbër që pulson. Muret nuk i sheh, i zbulon vetëm me tingull.",
        "p2_title": "Tingulli janë sytë e tu",
        "p2_text": "Çdo tingull lëshon një valë që ndriçon muret për një çast. Hapat bëjnë valë të vogla, duartrokitja një valë të madhe. Guri ndriçon vendin ku bie. Por çdo tingull e dëgjojnë edhe përbindëshat.",
        "p3_title": "Përbindëshat",
        "p3_text": "Janë të verbër, por dëgjojnë shumë mirë. I sheh vetëm kur i prek vala jote, dhe hapat e tyre lënë valë të kuqe. Kur njëri të dëgjon, ulërin dhe thërret të tjerët.",
        "p3_tip": "Këshillë: një gur anash i largon. Një gur që godet përbindëshin (E) e shkatërron; një gabim afër e bën të ikë. Zemra rreh më shpejt kur janë afër.",
        "ctl_move": "Lëvizja",
        "ctl_move_arrows": "Lëvizja (edhe me shigjeta)",
        "ctl_sneak": "Ecje e fshehtë (pa zhurmë)",
        "ctl_clap": "Duartrokitje",
        "ctl_stone": "Gur kur shigjeta tregon objektivin",
        "ctl_stone_aim": "Gur ku tregon",
        "state_flee": "Ikën",
        "ctl_mute": "Zëri aktiv/joaktiv",
        "ctl_pause": "Pauzë",
        "ctl_debug": "Modaliteti debug",
        "state_patrol": "Patrullon",
        "state_investigate": "Heton",
        "state_hunt": "Gjuan",
        "state_search": "Kërkon",
        "state_patrol_d": "ecën ngadalë",
        "state_investigate_d": "shkon drejt tingullit",
        "state_hunt_d": "vrapon drejt teje",
        "state_search_d": "të kërkon përreth",
        "p3_demo_hint": "↑ ↓  ose kliko: shiko dhe dëgjo çdo gjendje",
        "debug_sounds": "tinguj",
        "debug_monsters": "përbindësha",
        "intro_remember": "Të kujtojnë.",
        "debug_memory": "kujtesa (e vjetër / e re)",
        "dir_title": "Regjisori",
        "dir_build": "ndërtim",
        "dir_peak": "kulm",
        "dir_relax": "pushim",
        "dir_tension": "tension",
        "dir_calm": "qetësi",
        "hint_pressure": "presion",
        "hint_exit": "ruan daljen",
        "hint_relax": "pushim",
    },
    # ------------------------------------------------------------------ TR
    "tr": {
        "title": "YANKI",
        "lang_title": "Dil seçin",
        "lang_welcome": "Hoş geldiniz",
        "lang_detected": "sistemden algılandı",
        "lang_hint": "Enter  gösterileni aç   ·   ← →  veya fare  yönlendir",
        "tagline": "Ses senin gözlerin. Ve seni ele veren.",
        "menu_play": "Oyna",
        "menu_howto": "Nasıl oynanır",
        "menu_language": "Dil",
        "menu_sound_on": "Ses: açık",
        "menu_sound_off": "Ses: kapalı",
        "menu_quit": "Çıkış",
        "menu_level": "Bölüm {n} · {name}",
        "hint_nav": "↑ ↓  seç   ·   ← →  bölüm   ·   Enter  onayla",
        "hint_back": "Esc  geri",
        "level_label": "BÖLÜM {n}",
        "level_1": "Sessizlik",
        "level_2": "Fısıltılar",
        "level_3": "Av sahası",
        "hud_stones": "taş",
        "hud_clap": "alkış",
        "hud_pause": "Esc  duraklat",
        "pause_title": "DURAKLATILDI",
        "pause_resume": "Devam et",
        "pause_restart": "Baştan başla",
        "pause_menu": "Ana menü",
        "win_title": "KAÇTIN",
        "win_time": "Süre: {time}",
        "win_next": "Sonraki bölüm",
        "win_all": "Tüm bölümleri bitirdin.",
        "lose_title": "SENİ YAKALADI",
        "lose_sub": "Seni duydu.",
        "retry": "Tekrar dene",
        "howto_title": "Nasıl oynanır",
        "howto_pages": "← →  sayfalar   ·   Esc  geri",
        "p1_title": "Amaç",
        "p1_text": "Zifiri karanlık bir mağarada mahsur kaldın. Çıkışı bul: yanıp sönen yeşil ışığı. Duvarları göremezsin, onları yalnızca sesle keşfedersin.",
        "p2_title": "Ses senin gözlerin",
        "p2_text": "Her ses, duvarları bir anlığına aydınlatan bir dalga yayar. Adımlar küçük dalgalar, alkış büyük bir dalga yapar. Taş, düştüğü yeri aydınlatır. Ama her sesi canavarlar da duyar.",
        "p3_title": "Canavarlar",
        "p3_text": "Kördürler ama çok iyi duyarlar. Onları yalnızca senin dalgan onlara değdiğinde görürsün; adımları kırmızı dalgalar bırakır. Biri seni duyunca çığlık atar ve diğerlerini çağırır.",
        "p3_tip": "İpucu: kenara atılan taş dikkatlerini dağıtır. Canavara isabet eden taş (E) onu yok eder; yakına düşen taş onu kaçırır. Yakındayken kalbin daha hızlı atar.",
        "ctl_move": "Hareket",
        "ctl_move_arrows": "Hareket (oklarla da)",
        "ctl_sneak": "Sinsice yürü (sessiz)",
        "ctl_clap": "Alkış",
        "ctl_stone": "Ok hedefi gösterince taş at",
        "ctl_stone_aim": "Gösterdiğin yere taş at",
        "state_flee": "Kaçıyor",
        "ctl_mute": "Sesi aç/kapat",
        "ctl_pause": "Duraklat",
        "ctl_debug": "Debug modu",
        "state_patrol": "Devriye",
        "state_investigate": "Araştırıyor",
        "state_hunt": "Avlanıyor",
        "state_search": "Arıyor",
        "state_patrol_d": "yavaşça dolaşır",
        "state_investigate_d": "sese doğru gider",
        "state_hunt_d": "sana doğru koşar",
        "state_search_d": "etrafta seni arar",
        "p3_demo_hint": "↑ ↓  veya tıkla: her durumu izle ve dinle",
        "debug_sounds": "ses",
        "debug_monsters": "canavar",
        "intro_remember": "Seni hatırlıyorlar.",
        "debug_memory": "hafıza (eski / yeni)",
        "dir_title": "Yönetmen",
        "dir_build": "gerilim artıyor",
        "dir_peak": "zirve",
        "dir_relax": "dinlenme",
        "dir_tension": "gerilim",
        "dir_calm": "sakinlik",
        "hint_pressure": "baskı",
        "hint_exit": "çıkışı koru",
        "hint_relax": "dinlenme",
    },
}

_current = "mk"


def tr(key: str, **kwargs) -> str:
    """Го враќа текстот за клучот на тековниот јазик (со англиски како резерва)."""
    text = STRINGS.get(_current, {}).get(key) or STRINGS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text


def tr_in(lang: str, key: str) -> str:
    """Текст на конкретен јазик (за екранот за избор, каде се прикажуваат сите)."""
    return STRINGS.get(lang, {}).get(key) or STRINGS["en"].get(key, key)


def current() -> str:
    return _current


def set_language(code: str) -> None:
    global _current
    if code in STRINGS:
        _current = code
        save_settings({"language": code})


def detect_system_language() -> str:
    """Јазикот на оперативниот систем, ако го поддржуваме; инаку англиски.

    Windows враќа имиња како 'Macedonian_North Macedonia', а Linux/macOS
    кодови како 'mk_MK', па проверуваме и двата облика.
    """
    names = {"mk": ("mk", "macedon"), "sq": ("sq", "alban"), "tr": ("tr", "turk"), "en": ("en", "english")}
    try:
        loc = (locale.getlocale()[0] or "").lower()
    except (ValueError, TypeError):
        loc = ""
    for code, hints in names.items():
        if any(loc.startswith(h) for h in hints):
            return code
    return "en"


def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(changes: dict) -> None:
    data = load_settings()
    data.update(changes)
    try:
        SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass   # ако нема дозвола за запишување, играта сепак работи


def initial_language() -> tuple[str, str]:
    """(предложен јазик, препознаен системски јазик)."""
    detected = detect_system_language()
    saved = load_settings().get("language")
    return (saved if saved in STRINGS else detected), detected
