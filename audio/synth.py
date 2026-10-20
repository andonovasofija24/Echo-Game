"""Процедурална синтеза на звук: сите звуци во играта се генерираат со код.

Нема ниту една аудио датотека. Секој звук е листа од примероци (броеви од
-32768 до 32767) што ги пресметуваме од едноставни градивни блокови:
  - шум (random) за удари, чекори, плескање,
  - синусоиди за длабоки тонови (чекори на чудовиштето, срце, амбиент),
  - обвивка (envelope): колку брзо звукот почнува и згаснува,
  - нископропусен филтер: го прави шумот „потап“ (чекор наместо шушкање),
  - ехо: задоцнети, потивки копии од истиот звук (тематски за играта!).

Се користи само стандардниот модул `array`, без numpy.
"""

import math
import random
from array import array

SAMPLE_RATE = 22050


# ================= Градивни блокови =================

def silence(seconds: float) -> list[float]:
    return [0.0] * int(SAMPLE_RATE * seconds)


def noise(seconds: float, rng: random.Random) -> list[float]:
    return [rng.uniform(-1, 1) for _ in range(int(SAMPLE_RATE * seconds))]


def sine(freq: float, seconds: float, freq_end: float | None = None) -> list[float]:
    """Синусоида; ако е дадена freq_end, фреквенцијата лизга (pitch drop)."""
    n = int(SAMPLE_RATE * seconds)
    out, phase = [], 0.0
    for i in range(n):
        f = freq if freq_end is None else freq + (freq_end - freq) * i / n
        phase += 2 * math.pi * f / SAMPLE_RATE
        out.append(math.sin(phase))
    return out


def envelope(samples: list[float], attack: float, decay: float) -> list[float]:
    """Брз почеток (attack) и експоненцијално згаснување (decay), во секунди."""
    a = max(1, int(attack * SAMPLE_RATE))
    out = []
    for i, s in enumerate(samples):
        t = i / SAMPLE_RATE
        k = i / a if i < a else math.exp(-(t - attack) / decay)
        out.append(s * k)
    return out


def lowpass(samples: list[float], cutoff: float) -> list[float]:
    """Едноставен еднополен нископропусен филтер: ги задушува високите фреквенции."""
    rc = 1 / (2 * math.pi * cutoff)
    dt = 1 / SAMPLE_RATE
    alpha = dt / (rc + dt)
    out, y = [], 0.0
    for s in samples:
        y += alpha * (s - y)
        out.append(y)
    return out


def mix(*tracks: list[float]) -> list[float]:
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, s in enumerate(t):
            out[i] += s
    return out


def echo(samples: list[float], delay: float, feedback: float, repeats: int) -> list[float]:
    """Додава задоцнети копии од звукот, секоја потивка од претходната."""
    d = int(delay * SAMPLE_RATE)
    out = samples + [0.0] * (d * repeats)
    gain = 1.0
    for r in range(1, repeats + 1):
        gain *= feedback
        offset = d * r
        for i, s in enumerate(samples):
            out[offset + i] += s * gain
    return out


def normalize(samples: list[float], peak: float = 0.9) -> list[float]:
    m = max((abs(s) for s in samples), default=0)
    return samples if m == 0 else [s * peak / m for s in samples]


def to_stereo_bytes(samples: list[float]) -> bytes:
    """Float [-1, 1] → 16-битни цели броеви, дуплирани за лев и десен канал."""
    buf = array("h")
    for s in samples:
        v = int(max(-1.0, min(1.0, s)) * 32767)
        buf.append(v)
        buf.append(v)
    return buf.tobytes()


# ================= Звуци во играта =================

def make_step(rng: random.Random) -> list[float]:
    """Чекор: кус удар од филтриран шум + тивок длабок „туп“."""
    body = lowpass(noise(0.09, rng), 900)
    thump = sine(110, 0.09, 70)
    return normalize(envelope(mix(body, [s * 0.4 for s in thump]), 0.003, 0.025), 0.8)


def make_clap(rng: random.Random) -> list[float]:
    """Плескање: остар шум, а потоа ЕХО што се одбива од пештерата."""
    hit = envelope(lowpass(noise(0.12, rng), 3500), 0.001, 0.018)
    return normalize(echo(hit, delay=0.11, feedback=0.45, repeats=5))


def make_stone(rng: random.Random) -> list[float]:
    """Камче: три кликови како што отскокнува, со кратко ехо."""
    out = silence(0.25)
    for start, gain in ((0.0, 1.0), (0.07, 0.55), (0.12, 0.3)):
        click = envelope(lowpass(noise(0.03, rng), 5000), 0.0005, 0.006)
        offset = int(start * SAMPLE_RATE)
        for i, s in enumerate(click):
            out[offset + i] += s * gain
    return normalize(echo(out, delay=0.09, feedback=0.3, repeats=3), 0.7)


def make_monster_step(rng: random.Random) -> list[float]:
    """Чекор на чудовиште: многу длабок, тежок удар (фреквенцијата паѓа)."""
    boom = sine(70, 0.35, 35)
    grit = lowpass(noise(0.35, rng), 300)
    return normalize(envelope(mix(boom, [s * 0.5 for s in grit]), 0.005, 0.09))


def make_growl(rng: random.Random) -> list[float]:
    """Рикање кога чудовиштето ќе почне да лови: груб тон што трепери."""
    n = int(SAMPLE_RATE * 0.8)
    out, phase = [], 0.0
    for i in range(n):
        t = i / SAMPLE_RATE
        f = 85 - 30 * t + 6 * math.sin(2 * math.pi * 11 * t)   # тресење на гласот
        phase += f / SAMPLE_RATE
        saw = 2 * (phase % 1) - 1                               # „пилест“ бран = груб звук
        out.append(saw * (0.6 + 0.4 * math.sin(2 * math.pi * 23 * t)))
    rough = lowpass(mix(out, [s * 0.4 for s in noise(0.8, rng)]), 700)
    return normalize(envelope(rough, 0.05, 0.3))


def make_heartbeat() -> list[float]:
    """Срце (луб-дуб): играчот го слуша кога чудовиштето е блиску."""
    lub = envelope(sine(60, 0.12, 45), 0.005, 0.03)
    dub = envelope(sine(55, 0.12, 40), 0.005, 0.03)
    out = lub + silence(0.06) + [s * 0.7 for s in dub]
    return normalize(out, 0.9)


def make_ambient(rng: random.Random) -> list[float]:
    """Амбиент на пештерата: тивко брмчење што се повторува без пауза.

    Траењето е 8 секунди и сите фреквенции прават ЦЕЛ број циклуси во 8 s,
    па крајот точно се спојува со почетокот (seamless loop).
    """
    seconds = 8.0
    n = int(SAMPLE_RATE * seconds)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        swell = 0.6 + 0.4 * math.sin(2 * math.pi * t / seconds)       # 1 циклус
        s = (math.sin(2 * math.pi * 55 * t) * 0.5 +
             math.sin(2 * math.pi * 82.5 * t) * 0.3 +
             math.sin(2 * math.pi * 110.25 * t) * 0.15)
        out.append(s * swell)
    air = lowpass(noise(seconds, rng), 200)
    return normalize(mix(out, [s * 0.6 for s in air]), 0.5)


def make_win() -> list[float]:
    """Победа: растечки акорд, како светлина на крајот од тунелот."""
    out = silence(1.6)
    for k, freq in enumerate((523.25, 659.25, 783.99, 1046.5)):   # C-E-G-C
        tone = envelope(sine(freq, 1.2), 0.01, 0.4)
        offset = int(k * 0.1 * SAMPLE_RATE)
        for i, s in enumerate(tone):
            out[offset + i] += s * 0.4
    return normalize(echo(out, 0.15, 0.3, 2), 0.7)


def make_lose(rng: random.Random) -> list[float]:
    """Пораз: длабок удар и дисонантен крик."""
    hit = envelope(sine(90, 1.0, 30), 0.002, 0.25)
    screech = envelope(mix(sine(620, 0.9, 380), sine(655, 0.9, 400)), 0.01, 0.25)
    grit = envelope(lowpass(noise(1.0, rng), 2000), 0.001, 0.1)
    return normalize(mix(hit, [s * 0.35 for s in screech], [s * 0.4 for s in grit]))


def make_shriek(rng: random.Random) -> list[float]:
    """Крик: висок, пискав тон што трепери и паѓа, со ехо низ пештерата."""
    n = int(SAMPLE_RATE * 0.9)
    out, phase = [], 0.0
    for i in range(n):
        t = i / SAMPLE_RATE
        f = 900 - 420 * t + 60 * math.sin(2 * math.pi * 17 * t)
        phase += f / SAMPLE_RATE
        out.append(math.sin(2 * math.pi * phase) + 0.5 * (2 * (phase % 1) - 1))
    grit = lowpass(noise(0.9, rng), 2500)
    body = envelope(mix(out, [s * 0.5 for s in grit]), 0.02, 0.25)
    return normalize(echo(mix(body, make_growl(rng)[:n]), 0.16, 0.35, 3))


def make_monster_death(rng: random.Random) -> list[float]:
    """Уништено чудовиште: краток удар, па длабок рик што паѓа и се распаѓа во шум."""
    hit = envelope(lowpass(noise(0.15, rng), 3000), 0.001, 0.03)
    howl = envelope(sine(320, 1.1, 40), 0.01, 0.35)
    crumble = envelope(lowpass(noise(1.1, rng), 600), 0.05, 0.4)
    body = mix(hit, [s * 0.7 for s in howl], [s * 0.6 for s in crumble])
    return normalize(echo(body, 0.14, 0.3, 3))


def make_ui_move() -> list[float]:
    """Тивок „тик“ при движење низ менито."""
    return normalize(envelope(sine(1400, 0.05, 1100), 0.001, 0.012), 0.5)


def make_ui_select() -> list[float]:
    """Потврда: два тона нагоре со мало ехо (како сонар пинг)."""
    a = envelope(sine(660, 0.12), 0.002, 0.04)
    b = envelope(sine(990, 0.18), 0.002, 0.06)
    out = a + b
    return normalize(echo(out, 0.12, 0.3, 2), 0.6)


def build_all(seed: int = 7) -> dict[str, list[bytes]]:
    """Ги генерира сите звуци еднаш, на почетокот на играта.

    Чекорите имаат по неколку варијанти: истиот звук повторен илјада пати
    звучи вештачки, а мала разлика го прави природен.
    """
    rng = random.Random(seed)
    return {
        "step": [to_stereo_bytes(make_step(rng)) for _ in range(4)],
        "clap": [to_stereo_bytes(make_clap(rng))],
        "stone": [to_stereo_bytes(make_stone(rng)) for _ in range(2)],
        "monster_step": [to_stereo_bytes(make_monster_step(rng)) for _ in range(3)],
        "growl": [to_stereo_bytes(make_growl(rng))],
        "heartbeat": [to_stereo_bytes(make_heartbeat())],
        "ambient": [to_stereo_bytes(make_ambient(rng))],
        "win": [to_stereo_bytes(make_win())],
        "lose": [to_stereo_bytes(make_lose(rng))],
        "shriek": [to_stereo_bytes(make_shriek(rng))],
        "monster_death": [to_stereo_bytes(make_monster_death(rng))],
        "ui_move": [to_stereo_bytes(make_ui_move())],
        "ui_select": [to_stereo_bytes(make_ui_select())],
    }
