## Shots and cuts

`[Shot 1]` carries **no** timestamp. Every later shot begins with its exact cut time in the form `[Shot N] At MM:SS.mmm, `. The brief gives you the exact cut time for each shot — use those values verbatim and do not invent, shift or reformat them.

```
[Shot 2] At 00:03.500, the camera cuts to...
```

For ordinary cuts use `the camera cuts to`, `the shot cuts to`, `the shot transitions to`, `the shot changes to`, or `the shot switches to`. Use cross-dissolve, fade or wipe only when the brief asks for it. A cut must introduce new information about the subject, space, state, viewpoint or time. If only the distance or a slight angle needs to change, prefer camera motion over a cut.

## Camera motion

A complete camera-motion expression has a **motion type**, and optionally an **amplitude** and a **speed**. Omit amplitude and speed when they are medium/normal.

- Motion type: `Zoom In / Zoom Out`, `Push In / Pull Out`, `Pan Left / Pan Right`, `Truck Left / Truck Right`, `Tilt Up / Tilt Down`, `Pedestal Up / Pedestal Down`, `Arc Shot`, `Tracking Shot`, `Static Shot`, `Shake Slightly / Shake Strongly`, `POV`, `Roll Clockwise / Roll Counterclockwise`
- Amplitude: `with small amplitude`, `with large amplitude`
- Speed: `at slow speed`, `at fast speed`

Write camera motion as a natural English action inside the shot, not as labels appended to the sentence:

```
The camera pushes in with small amplitude at slow speed toward the folded letter in her hands.
The camera pans right with large amplitude at fast speed, revealing the open doorway.
```

## Speakers and dialogue

Every subject who speaks, sings or produces an off-screen human voice gets a stable ID such as `(S1)` or `(S2)`. The brief assigns the IDs — use exactly those. When already-numbered speakers vocalize together use a compound ID such as `(S1,S2)`. A speaker keeps the same ID across shots. Characters who never vocalize get no ID.

When a speaker first appears, establish a stable identity from what is visible and audible: character type, age, gender, whether they are on-screen, pitch, timbre, speaking rate, accent. Put the identifying phrase, ID, action and delivery **outside** `<d>`. Inside `<d>`, put only the language tag and the spoken content.

**Preserve every dialogue line exactly as the brief gives it — same characters, same punctuation, same language. Never translate, shorten or rewrite it.**

```
The young woman with a quiet, breathy voice (S1) says: <d>[Japanese] 次の駅で降りるね。</d>
The two children (S1,S2) shout together, <d>[English] Wait for us!</d>
```

For a voiceover, use the exact phrase `says in an off-screen voiceover`, and immediately after that `<d>` block state that the on-screen character's lips remain closed:

```
The man (S1) says in an off-screen voiceover: <d>[English] I still remember that road.</d> while his lips remain completely closed.
```

When one line crosses a cut, put `<scenetrans>` at the connecting point in both parts and state that the audio continues across the cut (`continues seamlessly across the cut`, `continues uninterrupted into the next shot`, `carries over from the previous shot`, `remains audible across the transition`). Use `<cutoff>` when speech is truncated by the end of the video.

## On-screen text

Any banner, sign, label, subtitle or neon text actually visible on screen goes in English double quotation marks, verbatim and untranslated:

```
A red neon sign reading "営業中" glows above the doorway.
```

# overall_soundscape

1-4 English sentences in one continuous paragraph summarizing ambient sound, physical action sounds and non-verbal human sounds across the whole video: wind, rain, traffic, footsteps, fabric movement, impacts, breathing, laughter, panting. Dialogue, singing and diegetic music belong in the main description and must not be repeated here. Use exactly `N/A` only when the brief requests complete silence.

```
Steady rain taps against the café windows while low room ambience continues underneath. The entrance bell rings once, followed by wet footsteps and the soft scrape of a chair.
```

# non_diegetic_music

1-3 English sentences describing background music that the characters cannot hear and only the audience can hear. Describe instrumentation, speed, rhythm and dynamic change. Do not use abstract mood words and do not explain the emotional function of the score. Singing, instruments, radio, television or phone music audible to the characters are diegetic and belong in the main description instead. Use exactly `N/A` when there is no non-diegetic music.

```
Sparse piano notes at a slow tempo, joined by sustained low strings that gradually increase in volume before fading out.
```
