# Yako eye screening: anemia triage from a photo of the eyelid

Anemia makes the inside of the lower eyelid (the palpebral conjunctiva) paler. This project measures that pallor on a
smartphone photo and turns it into a simple triage: **green** (low probability of anemia), **orange** (uncertain,
blood test advised) or **red** (high probability, blood test strongly advised).

It was developed and calibrated in Côte d'Ivoire, on patients with dark skin, and it runs today in the
[Yako](https://yako.app) health app. The goal is to bring a first screening step to women in places with no
laboratory nearby, starting with pharmacies.

> **Research prototype.** It is not a medical device and does not give a diagnosis. Only a blood test measures
> hemoglobin. Do not use it to rule out anemia in a pregnant woman or in someone with warning signs.

## How it works

```
photo ──► quality check ──► U-Net segmentation ──► skin-anchored colour ──► logistic ──► green / orange / red
          (blur, light)      (conjunctiva mask)     a_norm = a*(conj) − a*(skin)
```

1. **Quality check**: blur, exposure and resolution.
2. **Segmentation**: a U-Net with a ResNet-50 encoder finds the conjunctiva, with geometric checks on the mask
   (position, size, horizontal shape).
3. **Colour measure**: the white balance is set on the skin around the eye (grey-world), then
   `a_norm` = mean CIELAB a* of the conjunctiva minus mean a* of the skin. Anchoring on the patient's own skin makes the
   measure much less sensitive to the phone and the light. Specular reflections are removed, and skin pixels are
   filtered by colour so that a finger or hair in the frame does not bias the reference.
4. **Score**: a one-feature logistic regression gives the probability of anemia. Thresholds: green < 0.40 ≤ orange
   < 0.65 ≤ red.

The overlay shows what was measured: the conjunctiva in green and the skin reference in blue.

## Results

Cohort from Côte d'Ivoire, 2 sites, **152 patients, 34 with anemia** (hemoglobin from a blood count, WHO thresholds by
age and sex), photos taken with several Android and iPhone models. The full pipeline was run end to end, with
automatic segmentation, exactly as in this repository.

| Metric | Value |
|---|---|
| AUC | 0.70 (95% CI 0.60 to 0.79) |
| AUC, 5-fold cross-validation (20 repeats) | 0.69 |
| Sensitivity (anemic patients not classified green) | 0.87 |
| Specificity (non-anemic patients classified green) | 0.41 |
| Severe anemia (Hb < 9 g/dL) classified green | 0 of 6 |

Sensitivity and specificity are measured out of sample (5-fold cross-validation repeated 50 times).

What each colour means in this cohort (22% of patients with anemia):

| Result | Share of patients | Of whom anemic | Advice |
|---|---|---|---|
| Green | 34% | 9% | No test needed now, unless symptoms or pregnancy |
| Orange | 49% | 29% | Blood test advised |
| Red | 17% | 30% | Blood test strongly advised |

A green result divides the risk of anemia by about 2.4, so one patient in three can be spared a blood test. Orange and
red carry a similar risk today; both lead to a blood test.

**Choosing the threshold.** The green threshold sets the balance between missed anemia and unnecessary tests:

| Green threshold | Sensitivity | Specificity | Anemic patients classified green (of 34) |
|---|---|---|---|
| 0.30 | 0.96 | 0.27 | 1 |
| **0.40 (default)** | **0.87** | **0.41** | **4 to 5** |
| 0.50 | 0.67 | 0.57 | 11 |

0.40 is the highest threshold that keeps every severe case out of green. It can be changed in
`anemia_eye/model_calibration.json` (`t_green`). See [MODEL_CARD.md](MODEL_CARD.md) for the details and the
limitations.

## Quick start

Python 3.10 or later. CPU is enough (about one second per photo).

```bash
git clone <this repository> && cd yako-anemia-eye
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Command line (the 125 MB segmentation weights download on first run)
python predict.py my_eye_photo.jpg --overlay results/

# Web demo
uvicorn server:app --host 0.0.0.0 --port 8000
# then open http://localhost:8000
```

The web demo opens the camera directly in the page, on a computer (webcam) as on a phone, with an oval guide where
the pink inner eyelid should be. Choosing an existing photo is also possible.

On a phone, browsers allow the live camera only over https. To test from a phone on the same Wi-Fi:

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj "/CN=yako-demo" -keyout key.pem -out cert.pem
uvicorn server:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
# then open https://<your computer's IP>:8000 on the phone and accept the certificate warning
```

Over plain http, the page falls back to the phone's own camera app, which also works.

With Docker:

```bash
docker build -t yako-eye . && docker run -p 8000:8000 yako-eye
```

From Python:

```python
import cv2
from anemia_eye import AnemiaEye

eye = AnemiaEye()
r = eye.predict(cv2.imread('photo.jpg'))
print(r.ok, r.triage, r.probability, r.error)
```

Tests: `python -m pytest tests`.

### Taking a good photo

- Daylight or a bright room, no flash.
- Pull the lower eyelid down with one finger to show the pink inner part.
- Eye in the middle of the frame, with some skin visible around it.

When a photo cannot be used, the tool says why (too dark, blurry, conjunctiva not visible, off-centre) instead of
giving a result.

## Repository

| Path | Content |
|---|---|
| `anemia_eye/pipeline.py` | The whole pipeline: quality, segmentation, measure, score |
| `anemia_eye/model_calibration.json` | Logistic regression parameters (mean, scale, coefficient, intercept) |
| `predict.py` | Command line |
| `server.py`, `static/index.html` | Web demo (FastAPI) |
| `tests/` | Unit tests |

The segmentation weights are hosted on Hugging Face:
[pk180/anemiaeye-models](https://huggingface.co/pk180/anemiaeye-models) (`unet_resnet50_v2_fullframe.pt`). Their
SHA-256 is checked after download.

## Privacy

- No patient photo and no patient-level data are included in this repository.
- The demo server processes images in memory and does not store them.
- Only aggregate model parameters are published (four numbers in `model_calibration.json`).

## Roadmap

- Prospective validation in pharmacies, with blood tests for every participant.
- Larger cohort of women of reproductive age and pregnant women.
- Live guidance at capture time (already in the Yako app: countdown and automatic shot when the conjunctiva is
  visible, with the real reason when it is not).
- Combination with other signals (nail bed, symptoms) to raise specificity.

## Authors

Developed by [Meditect](https://meditect.com). Research, data collection and model by Issa Cissé.

## License

[MIT](LICENSE), © 2026 Meditect. Contributions and independent validations are welcome.

---

## En français

Yako analyse une photo de l'intérieur de la paupière inférieure pour repérer une pâleur liée à l'anémie, et donne un
tri simple : vert, orange ou rouge. Le modèle a été construit en Côte d'Ivoire, sur 152 patients à peau foncée, et
fonctionne aujourd'hui dans l'application Yako. C'est un prototype de recherche pour le dépistage, pas un diagnostic :
seule une prise de sang mesure l'hémoglobine. Installation et utilisation : voir *Quick start* ci-dessus.
