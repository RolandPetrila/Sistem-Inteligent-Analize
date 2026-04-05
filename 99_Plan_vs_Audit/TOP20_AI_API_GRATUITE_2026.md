# 🏆 TOP 20 API-uri AI Gratuite — Aprilie 2026
### Ghid complet cu limite, funcționalități și aplicații practice pentru proiectele tale

> **Actualizat:** Aprilie 2026 | **Criterii ranking:** capabilitate × limite gratuite × relevanță pentru proiectele tale  
> **Profilul tău:** Developer/antreprenor român · Stack: Python 3.13 + FastAPI + React 18 + Next.js · Proiecte active: RIS, Traduceri-Matematica, Livada, ITP Hall, Cake and Roll

---

## 📊 Tabel rapid de referință

| # | Provider | Tier gratuit | Card necesar | Modele flagship | Best for |
|---|---|---|---|---|---|
| 1 | Google Gemini | Rate-limited permanent | ❌ | Gemini 2.5 Pro/Flash | Prototipare, multimodal |
| 2 | xAI Grok | $25 signup + $150/lună | ❌ | Grok 4, Grok 4.1 Fast | Volum mare, context 2M |
| 3 | Groq | 14.400 req/zi (8B) | ❌ | Llama 4, Llama 3.3 70B | Viteză, real-time |
| 4 | DeepSeek | 5M tokens signup | ❌ | DeepSeek V4, R1 | Cod, reasoning ieftin |
| 5 | Mistral AI | 1B tokens/lună | ❌ (telefon) | Large 3, Codestral | Cod, EU GDPR |
| 6 | OpenRouter | 50–1000 req/zi | ❌ | 29+ modele :free | Multi-model gateway |
| 7 | Cerebras | 1M tokens/zi | ❌ | Llama 70B, Qwen 235B | Viteză extremă |
| 8 | Cohere | 1.000 req/lună | ❌ | Command R+, Embed 4 | RAG, embeddings |
| 9 | Cloudflare Workers AI | 10.000 neurons/zi | ❌ | FLUX.2, Llama, Whisper | Imagini, edge deploy |
| 10 | Hugging Face | 1.000 req/zi | ❌ | NLLB-200, Whisper, 1M+ | Traducere, modele speciale |
| 11 | SambaNova | $5 + free tier | ❌ | Llama 405B, Qwen 72B | Modele mari, viteză |
| 12 | NVIDIA NIM | 1.000 credite | ❌ | DeepSeek R1, Llama | Enterprise eval |
| 13 | Together AI | $100 credite | ❌ | Llama 4, DeepSeek V3 | 200+ open-source |
| 14 | GitHub Models | 50–150 req/zi | ❌ (GitHub) | GPT-4o, DeepSeek-R1 | GitHub ecosystem |
| 15 | Fireworks AI | 10 RPM free | ❌ | Llama 405B, DeepSeek | Inferență rapidă |
| 16 | Perplexity AI | Credite la signup | ❌ | Sonar Pro, Sonar | Search augmented AI |
| 17 | Google Vertex AI | $300 credite (90 zile) | ✅ | Gemini + toate | Enterprise, multimodal |
| 18 | Tavily | 1.000 req/lună | ❌ | Search API | Web search pentru agenți |
| 19 | Jina AI | 1M tokens | ❌ | Reader, Embeddings | Web scraping, RAG |
| 20 | Replicate | $5 credite | ❌ | FLUX, Whisper, SD | Imagini, audio, video |

---

## ⭐ TIER 1 — Esențiale (instalează imediat)

---

### #1 🟢 Google AI Studio (Gemini API)
**Cel mai generos free tier permanent din industrie**

**🔗 API Key:** https://aistudio.google.com/app/apikey  
**📖 Docs:** https://ai.google.dev/docs  
**🧰 SDK:** `pip install google-generativeai`

#### Limite gratuite (fără card, permanente)
| Model | RPM | RPD | Tokens input/req |
|---|---|---|---|
| Gemini 2.5 Pro | 5 | 25 | 1M tokens |
| Gemini 2.5 Flash | 15 | 1.000 | 1M tokens |
| Gemini 2.5 Flash-Lite | 30 | 1.500 | 1M tokens |
| Gemini Embedding | 5 | 100 | 2.048 tokens |

#### Ce face exact
- **Text + cod:** generare, analiză, debugging, explicații
- **Multimodal:** înțelege imagini, PDF-uri, audio, video în același request
- **Context 1M tokens:** poți trimite un întreg manual de matematică (~750.000 cuvinte) într-un singur request
- **Structured output:** răspunsuri direct în format JSON
- **Function calling:** Claude poate apela funcții din codul tău

#### Cum te ajută în proiectele tale

**📐 Traduceri-Matematica:**
```python
import google.generativeai as genai
genai.configure(api_key="AIza...")

model = genai.GenerativeModel('gemini-2.5-flash')

# Trimite o pagină PDF scanată și obții textul structurat
with open('pagina_manual.pdf', 'rb') as f:
    pdf_data = f.read()

response = model.generate_content([
    "Extrage textul din această pagină de manual matematic. "
    "Păstrează formulele LaTeX intacte. "
    "Returnează JSON cu câmpurile: text_paragraphe, formule_latex, titluri",
    {"mime_type": "application/pdf", "data": pdf_data}
])
```

**🌿 Livada (identificare boli):**
```python
# Trimite o fotografie și identifici boala
with open('frunza_bolnava.jpg', 'rb') as f:
    img = f.read()

response = model.generate_content([
    "Analizează această frunză de pom fructifer. "
    "Identifică: 1) Specia pomului 2) Boala sau dăunătorul prezent "
    "3) Tratamentul recomandat cu produse disponibile în România "
    "4) Urgența intervenției (1-10)",
    {"mime_type": "image/jpeg", "data": img}
])
```

**🏢 RIS (Romanian Intelligence System):**
```python
# Extrage date structurate din documente publice
response = model.generate_content([
    f"""Analizează acest document ANAF și extrage:
    - CUI, denumire, adresă
    - Cifra de afaceri pe ultimii 3 ani
    - Număr angajați
    - Stare juridică curentă
    Returnează JSON strict.
    Document: {document_text}"""
])
import json
firma_data = json.loads(response.text)
```

**⚠️ Limitare:** Datele tale pot fi folosite pentru îmbunătățirea modelelor pe tier gratuit. Activează billing (fără costuri automate) pentru a dezactiva asta.

---

### #2 🟡 xAI Grok API
**Cei mai mulți dolari gratuiți: $175 prima lună**

**🔗 API Key:** https://console.x.ai  
**📖 Docs:** https://docs.x.ai  
**🧰 SDK:** compatibil OpenAI (`openai` package cu base_url schimbat)

#### Credite gratuite
| Tip | Valoare | Condiție |
|---|---|---|
| Signup bonus | $25 | Automat la înregistrare |
| Data sharing program | $150/lună | Min $5 cheltuit + opt-in (irevocabil) |
| **Total prima lună** | **$175** | — |

#### Modele disponibile
| Model | Input | Output | Context |
|---|---|---|---|
| Grok 4 | $3/M | $15/M | 256K tokens |
| Grok 4.1 Fast | $0.20/M | $0.50/M | **2M tokens** |
| Grok 3 Mini | $0.10/M | $0.30/M | 128K tokens |

#### Ce face exact
- Context window **2M tokens** = cel mai mare din industrie (echivalent ~1.500 pagini de text)
- Acces **real-time la date X/Twitter** — știri, trending, postări recente
- Compatible 100% cu OpenAI SDK — schimbi doar `base_url`
- Function calling, structured output, streaming

#### Cum te ajută în proiectele tale

**🏢 RIS — analiză competitor cu date recente:**
```python
from openai import OpenAI

client = OpenAI(
    api_key="xai-...",
    base_url="https://api.x.ai/v1"
)

response = client.chat.completions.create(
    model="grok-4-1-fast",  # 2M context, cel mai ieftin
    messages=[{
        "role": "user",
        "content": f"""Analizează firma {nume_firma} din România.
        Caută informații recente pe X/Twitter și web despre:
        - Știri recente despre companie
        - Reputație și recenzii
        - Probleme legale sau financiare
        - Competitori principali
        Surse: ultimele 30 zile."""
    }]
)
```

**⚠️ Atenție critică:** Data sharing = xAI folosește prompt-urile tale pentru antrenament. **Nu folosi pentru date confidențiale ale clienților** (ITP, facturare, date personale). Folosește-l pentru cercetare publică (RIS cu date ANAF publice = OK).

---

### #3 ⚡ Groq
**Cea mai rapidă inferență gratuită: 500+ tokens/secundă**

**🔗 API Key:** https://console.groq.com/keys  
**📖 Docs:** https://console.groq.com/docs  
**🧰 SDK:** `pip install groq`

#### Limite gratuite (fără card, permanente)
| Model | RPM | RPD | TPM | Calitate |
|---|---|---|---|---|
| llama-3.1-8b-instant | 30 | **14.400** | 20.000 | Bună pt sarcini simple |
| llama-3.3-70b-versatile | 30 | 1.000 | 12.000 | **Excelentă** |
| llama-4-scout-17b | 30 | 1.000 | 30.000 | Nouă, multimodal |
| whisper-large-v3 | — | 2.000 | — | STT: 2h audio/oră |
| whisper-large-v3-turbo | — | 2.000 | — | STT rapid |

#### Ce face exact
- **Inferență LPU** (Language Processing Unit) — chip dedicat pentru AI, nu GPU standard
- **500-2000 tokens/sec** vs 50-100 tokens/sec la alți provideri
- Speech-to-text cu Whisper — transcrie audio în text cu acuratețe foarte bună
- Streaming răspunsuri în timp real
- Compatibil OpenAI SDK

#### Cum te ajută în proiectele tale

**🍰 Cake and Roll — chatbot rapid pentru clienți:**
```python
from groq import Groq

client = Groq(api_key="gsk_...")

def raspunde_client(intrebare: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # 14.400 req/zi, ultra-rapid
        messages=[
            {"role": "system", "content": 
             "Ești asistentul restaurantului Cake and Roll AFI Arad. "
             "Răspunzi în română. Meniu: pizza, paste, burgeri, deserturi. "
             "Program: L-D 10:00-22:00. Tel: 0724..."},
            {"role": "user", "content": intrebare}
        ],
        max_tokens=200,
        stream=False
    )
    return response.choices[0].message.content

# Răspuns în < 0.5 secunde
print(raspunde_client("Ce pizza aveți fără gluten?"))
```

**🏗️ ITP Hall — transcriere audio documente:**
```python
# Transcrie un document audio (instrucțiuni, rapoarte vocale)
with open("nota_tehnica.mp3", "rb") as f:
    transcriptie = client.audio.transcriptions.create(
        model="whisper-large-v3",
        file=f,
        language="ro",  # Română
        response_format="text"
    )
print(transcriptie)  # Text din audio, în < 5 secunde
```

**📐 Traduceri-Matematica — procesare rapidă batch:**
```python
import asyncio
from groq import AsyncGroq

# Procesează 100 de paragrafe în paralel, rapid
async def traduce_paragraf(client, paragraf: str) -> str:
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", 
                   "content": f"Traduce din română în slovacă: {paragraf}"}]
    )
    return response.choices[0].message.content
```

---

### #4 🧠 DeepSeek API
**Cel mai ieftin model frontier, reasoning excepțional**

**🔗 API Key:** https://platform.deepseek.com/api_keys  
**📖 Docs:** https://api-docs.deepseek.com  
**🧰 SDK:** compatibil OpenAI

#### Tier gratuit
| Ce primești | Valoare |
|---|---|
| Tokens la signup | **5 milioane tokens** (~$8.40 valoare) |
| Valabilitate | 30 zile |
| Rate limits în trial | Fără limită strictă |

#### Modele și prețuri (după epuizare credite)
| Model | Input | Output | Context | Best for |
|---|---|---|---|---|
| DeepSeek V4 | $0.30/M | $0.50/M | **1M tokens** | General, cod |
| DeepSeek R1 | $0.55/M | $2.19/M | 128K | **Reasoning** |
| DeepSeek V3.2 | $0.28/M | $0.42/M | 64K | Budget |
| Cache hit V4 | **$0.03/M** | — | — | Prompt repetat |

#### Ce face exact
- **DeepSeek R1** = model de reasoning (gândire pas-cu-pas) comparabil cu o1/o3 OpenAI, dar **96% mai ieftin**
- **Cache hit pricing:** dacă sistemul tău prompt e fix, plătești de 10x mai puțin pe input
- **Fără rate limits stricte** — servesc orice request pot (pot apărea 503 la vârf)
- **Off-peak discount:** 50-75% reducere între 16:30-00:30 GMT
- ⚠️ Serverele sunt în China — latență variabilă pentru Europa

#### Cum te ajută în proiectele tale

**🏢 RIS — analiză financiară avansată:**
```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-...",
    base_url="https://api.deepseek.com"
)

# R1 pentru analiză complexă (reasoning)
response = client.chat.completions.create(
    model="deepseek-reasoner",  # DeepSeek R1
    messages=[{
        "role": "user",
        "content": f"""Analizează situația financiară a firmei cu datele:
        Cifra afaceri 2023: {ca_2023} RON
        Cifra afaceri 2024: {ca_2024} RON  
        Datorii: {datorii} RON
        Angajați: {angajati}
        
        Evaluează: risc de insolvență, tendință, recomandare parteneriat.
        Explică raționamentul pas cu pas."""
    }]
)
# R1 returnează <think>...</think> + răspuns final
print(response.choices[0].message.content)
```

**📐 Traduceri-Matematica — cod complex:**
```python
# V4 pentru generare cod Python complex
response = client.chat.completions.create(
    model="deepseek-chat",  # DeepSeek V4
    messages=[{
        "role": "system", 
        "content": "Ești expert Python. Cod clean, tipat, cu docstrings."
    }, {
        "role": "user",
        "content": "Scrie un FormulaGuard complet care detectează LaTeX în DOCX"
    }]
)
```

---

### #5 🇪🇺 Mistral AI
**Cel mai bun provider european, excelent pentru cod**

**🔗 API Key:** https://console.mistral.ai/api-keys  
**📖 Docs:** https://docs.mistral.ai  
**🧰 SDK:** `pip install mistralai`

#### Tier gratuit — plan "Experiment"
| Limită | Valoare |
|---|---|
| Tokeni/lună | **1 miliard** |
| RPM | 2 req/minut |
| TPM | 500.000 tokens/minut |
| Card necesar | ❌ (doar verificare telefon) |
| Data residency | 🇪🇺 Europa |

#### Modele disponibile gratuit
| Model | Specialitate | Context |
|---|---|---|
| Mistral Large 3 | General, multilingv | 128K |
| Mistral Small 3.1 | Eficient, rapid | 128K |
| **Codestral** | **Cod specializat** | 256K |
| Pixtral 12B | Vizual (imagini) | 128K |
| Ministral 8B | Mic, rapid | 128K |
| Mistral Embed | Embeddings | 8K |
| Mistral OCR | Extragere text PDF | — |

#### Ce face exact
- **Codestral** = cel mai bun model specializat GRATUIT pentru cod (fill-in-middle, autocompletare)
- **Mistral OCR** = extrage text din PDF-uri scanate cu layout preservation
- **EU data residency** = datele rămân în Europa (relevant pentru GDPR)
- Prompts NU sunt folosite pentru antrenament pe plan Experiment (spre deosebire de alții)

#### Cum te ajută în proiectele tale

**📐 Traduceri-Matematica — OCR din PDF-uri:**
```python
from mistralai import Mistral

client = Mistral(api_key="...")

# Extrage text din PDF scanat cu layout preservation
with open("manual_matematica.pdf", "rb") as f:
    pdf_bytes = f.read()

import base64
pdf_b64 = base64.b64encode(pdf_bytes).decode()

response = client.ocr.process(
    model="mistral-ocr-latest",
    document={
        "type": "document_url",
        "document_url": f"data:application/pdf;base64,{pdf_b64}"
    },
    include_image_base64=True
)

# Returnează text structurat cu Markdown
for page in response.pages:
    print(page.markdown)  # Text cu formule și layout
```

**🏢 RIS — extragere date din documente scanate:**
```python
# Procesează documente ANAF/ONRC scanate
response = client.ocr.process(
    model="mistral-ocr-latest",
    document={"type": "document_url", "document_url": url_document}
)
text_extras = "\n".join([p.markdown for p in response.pages])

# Analizează cu Large pentru structurare
analiza = client.chat.complete(
    model="mistral-large-latest",
    messages=[{
        "role": "user",
        "content": f"Extrage JSON cu datele firmei din: {text_extras}"
    }]
)
```

**💻 Cod automat cu Codestral (VS Code compatible):**
```python
# Fill-in-middle pentru autocompletare cod
response = client.fim.complete(
    model="codestral-latest",
    prompt="def translate_ro_sk(text: str) -> str:\n    ",
    suffix="\n    return translated",
    max_tokens=200
)
print(response.choices[0].message.content)
```

---

## 🔵 TIER 2 — Foarte utile (instalează în primele 2 săptămâni)

---

### #6 🔀 OpenRouter
**Un singur API key pentru 200+ modele**

**🔗 API Key:** https://openrouter.ai/keys  
**📖 Docs:** https://openrouter.ai/docs  
**🧰 SDK:** compatibil OpenAI (`base_url="https://openrouter.ai/api/v1"`)

#### Tier gratuit
| Limită | Fără sold | Cu $10+ în cont |
|---|---|---|
| Req/zi (modele :free) | 50 | **1.000** |
| RPM | 20 | 20 |
| Card | ❌ | Opțional |

#### Modele gratuite notabile (aprilie 2026)
```
google/gemma-3-27b:free          — Google, 27B parametri
meta-llama/llama-3.3-70b:free    — Meta, calitate GPT-4 level
deepseek/deepseek-r1:free        — Reasoning puternic
deepseek/deepseek-v3:free        — General excellent
qwen/qwen3-235b:free             — Alibaba, 235B parametri
nvidia/nemotron-3-super:free     — NVIDIA, 262K context
openai/gpt-oss-120b:free         — OpenAI open-weight, Apache 2.0
mistralai/mistral-small-3.1:free — Mistral, eficient
```

#### Ce face exact
- **Un singur endpoint** pentru toți providerii: OpenAI, Anthropic, Google, Meta, etc.
- **A/B testing automat** între modele cu același cod
- **Fallback automat:** dacă un model pică, treci pe altul instant
- Router `openrouter/free` = alege automat cel mai bun model gratuit disponibil

#### Cum te ajută în proiectele tale

**🏢 RIS — testare model optim pentru extragere date:**
```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-or-...",
    base_url="https://openrouter.ai/api/v1"
)

# Testezi 3 modele cu același prompt, compari calitatea
modele = [
    "deepseek/deepseek-r1:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free"
]

prompt = f"Extrage din textul următor: CUI, denumire, adresă: {text_firma}"

for model in modele:
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    print(f"\n--- {model} ---\n{r.choices[0].message.content}")
```

**📐 Traduceri-Matematica — fallback automat:**
```python
# Dacă Gemini e la limită, trece pe Llama, dacă și ăsta e la limită, pe DeepSeek
response = client.chat.completions.create(
    model="openrouter/auto",  # Selectează automat
    messages=[{"role": "user", "content": f"Traduce: {paragraf}"}],
    extra_headers={
        "X-OR-Fallback": "meta-llama/llama-3.3-70b:free,deepseek/deepseek-v3:free"
    }
)
```

---

### #7 🚀 Cerebras
**Inferență ultra-rapidă pe chip wafer-scale**

**🔗 API Key:** https://cloud.cerebras.ai  
**📖 Docs:** https://inference-docs.cerebras.ai  
**🧰 SDK:** `pip install cerebras-cloud-sdk`

#### Tier gratuit (fără card, permanent)
| Limită | Valoare |
|---|---|
| Tokens/zi | **1 milion** |
| RPM | 30 |
| RPD | 14.400 |
| Viteză | **~2.000 tokens/sec** |

#### Modele disponibile
- `llama3.3-70b` — 70B parametri, calitate excelentă
- `llama3.1-8b` — rapid, limită zilnică mai mare
- `qwen-3-32b` — Alibaba, reasoning bun
- `deepseek-r1-distill-llama-70b` — Reasoning, rapid

#### Ce face exact
- **Chip wafer-scale** = un singur chip cât un wafer semiconductor întreg, pentru inferență
- Viteza de **2000 tokens/sec** = de 40x mai rapid decât GPU standard
- Util pentru streaming text lung în timp real (nu mai aștepți)
- OpenAI-compatible API

#### Cum te ajută

**🍰 Cake and Roll — răspunsuri instant chatbot:**
```python
from cerebras.cloud.sdk import Cerebras

client = Cerebras(api_key="csk-...")

# Streaming ultra-rapid — clientul vede textul apărând imediat
stream = client.chat.completions.create(
    messages=[{"role": "user", "content": intrebare_client}],
    model="llama3.3-70b",
    stream=True
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

---

### #8 📚 Cohere
**Cel mai bun pentru RAG și sisteme de căutare**

**🔗 API Key:** https://dashboard.cohere.com/api-keys  
**📖 Docs:** https://docs.cohere.com  
**🧰 SDK:** `pip install cohere`

#### Tier gratuit (fără card, permanent)
| Capabilitate | Limită gratuită |
|---|---|
| Generate (Command R+) | 20 RPM, 1.000 req/lună |
| Embed (vectorizare) | 100 RPM, fără limită lunară strictă |
| Rerank (reordonare) | 100 RPM, fără limită lunară strictă |
| Classify | 100 RPM |

#### Modele disponibile
| Model | Tip | Ce face |
|---|---|---|
| `command-r-plus` | Generate | Răspunsuri cu citare din documente |
| `command-a` | Generate | Cel mai nou, agentic |
| `embed-v4` | Embeddings | Transformă text în vectori |
| `rerank-v3.5` | Reranking | Reordonează rezultate căutare |
| `aya-expanse-32b` | Multilingv | 23 limbi inclusiv română |

#### Ce face exact — pipeline RAG complet gratuit
```
Document → Embed (vectorizare) → stocare în vector DB
Întrebare → Embed → căutare → top 20 rezultate
           → Rerank → top 5 relevante
           → Command R+ → răspuns cu citat din sursă
```

#### Cum te ajută în proiectele tale

**🏢 RIS — sistem de căutare inteligentă în documente firme:**
```python
import cohere

co = cohere.Client("co-...")

# PASUL 1: Vectorizează documentele firmelor
documente = [
    "Firma X SRL, CUI 12345, str. Aradului 1, CA 2024: 500.000 RON...",
    "Firma Y SA, CUI 67890, Timișoara, CA 2024: 2.000.000 RON...",
    # ... sute de documente
]

embeddings = co.embed(
    texts=documente,
    model="embed-v4",
    input_type="search_document"
).embeddings
# Stochezi embeddings în SQLite cu extensia sqlite-vss sau ChromaDB

# PASUL 2: La interogare
query = "firme de construcții din Arad cu CA > 1M RON"
query_embed = co.embed(
    texts=[query],
    model="embed-v4",
    input_type="search_query"
).embeddings[0]

# Găsești top 20 similare prin cosine similarity
# ...

# PASUL 3: Rerank pentru precizie
results = co.rerank(
    model="rerank-v3.5",
    query=query,
    documents=top_20_documente,
    top_n=5
)

# PASUL 4: Generare răspuns cu citare
response = co.chat(
    model="command-r-plus",
    message=query,
    documents=[{"text": r.document["text"]} for r in results.results]
)
print(response.text)  # Răspuns cu [1], [2] citări automate
```

---

### #9 ☁️ Cloudflare Workers AI
**Imagini FLUX gratuit + inferență la edge global**

**🔗 API Key:** https://dash.cloudflare.com → Workers & Pages → Workers AI  
**📖 Docs:** https://developers.cloudflare.com/workers-ai  
**🧰 SDK:** REST API direct sau `npm install @cloudflare/ai`

#### Tier gratuit
| Limită | Valoare |
|---|---|
| Neurons/zi | **10.000** |
| Imagini FLUX/zi | **~100-200 imagini** |
| Text requests (8B)/zi | **~1.000-2.000** |
| Reset | zilnic la 00:00 UTC |
| Card | ❌ |

#### Modele imagini disponibile
| Model | Calitate | Viteză |
|---|---|---|
| `@cf/black-forest-labs/flux-1-schnell` | Bună | Ultra-rapid |
| `@cf/black-forest-labs/flux-2-dev` | **Excelentă** | Mediu |
| `@cf/black-forest-labs/flux-2-klein` | Excelentă | Rapid + editare |

#### Cum generezi imagini gratuit

```python
import requests, base64

ACCOUNT_ID = "..."
API_TOKEN = "..."

def genereaza_imagine(prompt: str, filename: str):
    response = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/"
        "@cf/black-forest-labs/flux-1-schnell",
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        json={"prompt": prompt, "steps": 4}
    )
    
    result = response.json()
    img_b64 = result["result"]["image"]
    
    with open(filename, "wb") as f:
        f.write(base64.b64decode(img_b64))
    
    print(f"✅ Salvat: {filename}")

# Exemple practice pentru tine:
genereaza_imagine(
    "professional food truck exterior, Romanian street food, modern design, AFI mall",
    "food_truck_promo.png"
)

genereaza_imagine(
    "apple orchard in autumn, fruit trees, Romanian countryside, professional photo",
    "livada_promo.jpg"
)
```

#### ⚠️ Calculator neurons pentru imagini
- FLUX Schnell (4 steps) = ~50 neurons/imagine → **200 imagini/zi gratuit**
- FLUX Dev (20 steps) = ~200 neurons/imagine → **50 imagini/zi gratuit**
- Text Llama 3.2 3B = ~5 neurons/request → **2.000 req/zi gratuit**

---

### #10 🤗 Hugging Face Inference API
**Acces la mii de modele specializate, esențial pentru ro→sk**

**🔗 API Key:** https://huggingface.co/settings/tokens  
**📖 Docs:** https://huggingface.co/docs/api-inference  
**🧰 SDK:** `pip install huggingface_hub`

#### Tier gratuit
| Limită | Valoare |
|---|---|
| Req/zi | 1.000 |
| Modele disponibile | 1M+ |
| Card | ❌ |
| Cold start | 30-60s pentru modele neîncărcate |

#### Modele cheie pentru proiectele tale
| Model | Task | Unde folosești |
|---|---|---|
| `facebook/nllb-200-distilled-1.3B` | Traducere ro→sk direct | Traduceri-Matematica |
| `facebook/nllb-200-3.3B` | Traducere calitate mai bună | Producție |
| `openai/whisper-large-v3` | Speech-to-text | ITP, Livada |
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | Embeddings multilingv | RIS |
| `microsoft/trocr-large-handwritten` | OCR scris de mână | Documente vechi |

#### Cum traduci ro→sk fără pivot prin engleză

```python
import requests

API_URL = "https://api-inference.huggingface.co/models/facebook/nllb-200-distilled-1.3B"
headers = {"Authorization": "Bearer hf_..."}

def traduce_ro_sk(text: str) -> str:
    """Traducere directă română → slovacă cu NLLB-200"""
    response = requests.post(
        API_URL,
        headers=headers,
        json={
            "inputs": text,
            "parameters": {
                "src_lang": "ron_Latn",   # Română
                "tgt_lang": "slk_Latn",   # Slovacă
                "max_length": 512
            }
        }
    )
    return response.json()[0]["translation_text"]

# Exemplu pentru Traduceri-Matematica
text_ro = "Fie funcția f definită pe mulțimea numerelor reale."
text_sk = traduce_ro_sk(text_ro)
print(text_sk)
# Output: "Nech je funkcia f definovaná na množine reálnych čísel."
```

---

## 🟡 TIER 3 — Utile pentru cazuri specifice

---

### #11 🏎️ SambaNova Cloud
**Modele URIAȘE gratuit: Llama 405B accesibil**

**🔗 API Key:** https://cloud.sambanova.ai  
**📖 Docs:** https://docs.sambanova.ai  
**Tier gratuit:** $5 credite (30 zile) + free tier permanent cu rate limits

#### Modele disponibile gratuit
- `Meta-Llama-3.1-405B-Instruct` — **405 miliarde parametri!**
- `Meta-Llama-3.3-70B-Instruct`
- `Qwen2.5-72B-Instruct`
- `DeepSeek-R1` (distilled)

#### Limite free tier permanent
| Model | RPM | RPD |
|---|---|---|
| 405B | 10 | 500 |
| 70B | 30 | 1.000 |
| 8B | 30 | 5.000 |

**Când îl folosești:** când ai nevoie de calitate maximă pentru o sarcină complexă (405B = cel mai bun open-source disponibil gratuit) și nu contează viteza.

---

### #12 🟢 NVIDIA NIM
**Acces la modele enterprise cu 1.000 credite gratuite**

**🔗 API Key:** https://build.nvidia.com  
**📖 Docs:** https://docs.api.nvidia.com  
**Tier gratuit:** 1.000 credite signup + poți cere 4.000 extra = 5.000 total

#### Modele notabile
- `deepseek-ai/deepseek-r1` — Reasoning
- `meta/llama-3.3-70b-instruct`
- `nvidia/nemotron-3-super` — NVIDIA propriu
- `mistralai/mistral-large` — Enterprise Mistral
- Modele domeniu-specific: chimie, biologie, cod

**RPM:** 40 requests/minut  
**Când îl folosești:** evaluare modele enterprise, testare înainte de deployment, modele specifice NVIDIA.

---

### #13 💰 Together AI
**$100 credite la signup + 200+ modele open-source**

**🔗 API Key:** https://api.together.ai/settings/api-keys  
**📖 Docs:** https://docs.together.ai  
**🧰 SDK:** `pip install together`

**Tier gratuit:** $100 credite la înregistrare (fără card)

#### De ce e util
- Acces la **200+ modele open-source** prin un singur API
- Llama 4 Maverick, DeepSeek V3, Qwen3, Mixtral — toate disponibile
- Prețuri foarte mici după epuizarea creditelor ($0.20/M tokens pentru modele mid)
- Batch processing API cu 50% reducere

**Exemplu cost:** $100 credite = ~500 milioane tokens cu Llama 3.3 70B = luni de utilizare dev normală.

---

### #14 👨‍💻 GitHub Models
**Testare rapidă în ecosistemul GitHub/VS Code**

**🔗 Acces:** https://github.com/marketplace/models  
**📖 Docs:** https://docs.github.com/en/github-models  
**Condiție:** Cont GitHub gratuit

#### Modele disponibile (selecție)
- GPT-4o, GPT-4.1 (OpenAI)
- o3, o3-mini (OpenAI reasoning)
- Grok-3 (xAI)
- DeepSeek-R1
- Llama 3.3 70B (Meta)
- Phi-4 (Microsoft)

#### Limite
| Model tier | RPM | RPD | Tokens/req |
|---|---|---|---|
| High (GPT-4o, o1) | 10 | 50 | 8K input / 4K output |
| Low (Llama, Phi) | 15 | 150 | 8K input / 4K output |

**Când îl folosești:** testare rapidă înainte de a integra un model în cod, playground vizual din browser, integrare naturală cu GitHub Copilot workflow în VS Code.

---

### #15 🔥 Fireworks AI
**Inferență rapidă pentru open-source, inclusiv modele mari**

**🔗 API Key:** https://fireworks.ai/account/api-keys  
**📖 Docs:** https://docs.fireworks.ai  
**Tier gratuit:** 10 RPM fără card (6.000 RPM cu card adăugat)

#### Modele notabile
- `accounts/fireworks/models/llama-v3p1-405b-instruct` — 405B!
- `accounts/fireworks/models/deepseek-r1`
- `accounts/fireworks/models/qwen3-235b`

**Când îl folosești:** când vrei Llama 405B rapid și gratuit (10 req/min = suficient pentru dev).

---

## 🟠 TIER 4 — Specializate

---

### #16 🔍 Perplexity AI Sonar API
**AI cu acces real-time la internet + citări**

**🔗 API Key:** https://www.perplexity.ai/settings/api  
**📖 Docs:** https://docs.perplexity.ai  
**Tier gratuit:** credite la signup (variabile)

#### Ce face UNIC față de toate celelalte
- Răspunsuri **cu surse citate** din web, actualizate în timp real
- Nu are knowledge cutoff — știe ce s-a întâmplat azi
- Returnează URL-uri la sursele folosite

#### Modele
| Model | Ce face |
|---|---|
| `sonar` | Căutare web rapidă |
| `sonar-pro` | Căutare profundă, mai multe surse |
| `sonar-reasoning` | Căutare + reasoning pas cu pas |

#### Cum te ajută

**🏢 RIS — date actuale despre firme:**
```python
from openai import OpenAI

client = OpenAI(
    api_key="pplx-...",
    base_url="https://api.perplexity.ai"
)

response = client.chat.completions.create(
    model="sonar-pro",
    messages=[{
        "role": "user",
        "content": f"Caută informații actuale despre firma {nume_firma} România. "
                   f"Includ: știri recente, situație financiară, litigii, management."
    }]
)

# Răspuns cu citări din surse verificate
print(response.choices[0].message.content)
# Include [1] [2] [3] cu link-uri la surse
```

---

### #17 ☁️ Google Vertex AI
**$300 credite pentru 90 zile — toate modelele Google**

**🔗 Signup:** https://cloud.google.com/vertex-ai  
**📖 Docs:** https://cloud.google.com/vertex-ai/docs  
**Tier gratuit:** $300 credite 90 zile (card necesar, dar nu ești facturat în trial)

#### De ce diferă de Google AI Studio
- Gemini 2.5 Pro fără rate limits (plătit din $300 credite)
- Acces la modele de traducere, speech, vision dedicate
- Translation API: **500.000 caractere/lună gratuit permanent** — perfect pentru ro→sk
- Speech-to-Text: 60 min audio/lună gratuit permanent
- Vision AI: 1.000 unități/lună gratuit permanent

**Notă:** Necesită card dar nu ești facturat în trial. Dacă folosești doar serviciile cu free tier permanent, nu ești facturat nici după trial.

---

### #18 🕷️ Tavily Search API
**Web search pentru agenți AI — esențial pentru RIS**

**🔗 API Key:** https://app.tavily.com  
**📖 Docs:** https://docs.tavily.com  
**Tier gratuit:** **1.000 req/lună** (fără card)

#### Ce face exact
- **Search API pentru LLM-uri:** returnează rezultate web formatate optim pentru AI (nu HTML brut)
- Extract: extrage conținut de pe URL specific
- Filtrare după domeniu, dată, tip conținut
- Returnează snippet, URL, titlu, scor relevanță

#### Cum te ajută

**🏢 RIS — cercetare automată firme:**
```python
from tavily import TavilyClient

client = TavilyClient(api_key="tvly-...")

# Caută informații despre o firmă
results = client.search(
    query=f"{nume_firma} Romania ANAF bilant angajati",
    search_depth="advanced",
    max_results=10,
    include_domains=["anaf.ro", "onrc.ro", "listafirme.ro", "termene.ro"]
)

for r in results["results"]:
    print(f"📌 {r['title']}")
    print(f"🔗 {r['url']}")
    print(f"📝 {r['content'][:300]}\n")
```

**Integrare cu Claude/LangGraph pentru RIS:**
```python
# În LangGraph, Tavily e tool-ul standard de search
from langchain_community.tools.tavily_search import TavilySearchResults

search_tool = TavilySearchResults(max_results=5)
# Claude Code folosește automat acest tool când ai nevoie de info recente
```

---

### #19 🦁 Jina AI
**Web scraping + embeddings gratuit — pentru colectare date RIS**

**🔗 API Key:** https://jina.ai  
**📖 Docs:** https://docs.jina.ai  
**Tier gratuit:** **1 milion tokens** (fără card)

#### Servicii incluse
| Serviciu | Ce face | Limită gratuită |
|---|---|---|
| `r.jina.ai/{url}` | Convertește orice pagină web în Markdown curat | 1M tokens/cont |
| Embeddings API | Vectorizare text multilingv | Inclus în 1M |
| Reranker | Similar Cohere Rerank | Inclus |
| Classifier | Clasificare text | Inclus |

#### Cum te ajută

**🏢 RIS — extragere date de pe site-uri firme:**
```python
import requests

# Convertește pagina web a firmei în text curat pentru LLM
def extrage_pagina_firma(url: str) -> str:
    r = requests.get(
        f"https://r.jina.ai/{url}",
        headers={"Authorization": "Bearer jina_..."}
    )
    return r.text  # Markdown curat, fără HTML

# Exemplu
continut = extrage_pagina_firma("https://www.firma-x.ro/despre-noi")
# Obții textul curat pentru a-l trimite la un LLM
```

**Alternativă gratuită fără API key:**
```
GET https://r.jina.ai/https://www.site.ro
```
Funcționează fără autentificare cu limită mai mică.

---

### #20 🎨 Replicate
**Imagini, video, audio — toate modelele open-source**

**🔗 API Key:** https://replicate.com/account/api-tokens  
**📖 Docs:** https://replicate.com/docs  
**Tier gratuit:** $5 credite la signup (fără card)

#### Modele disponibile (plătit din $5 credite)
| Model | Task | Cost/imagine |
|---|---|---|
| FLUX 1.1 Pro | Imagini realiste | ~$0.04 |
| FLUX Schnell | Imagini rapide | ~$0.003 |
| Stable Diffusion 3.5 | Imagini artistice | ~$0.035 |
| Whisper | Speech-to-text | ~$0.001/minut |
| MusicGen | Generare muzică | ~$0.01 |

#### Cum te ajută

**🍰 Cake and Roll — materiale marketing:**
```python
import replicate

# Generează imagine promo cu $5 credite gratuite
output = replicate.run(
    "black-forest-labs/flux-schnell",
    input={
        "prompt": "modern food truck, gourmet street food, Romanian cuisine, "
                  "professional photography, warm lighting, appetizing",
        "width": 1024,
        "height": 1024,
        "num_outputs": 1
    }
)
# output[0] = URL la imaginea generată (expiră în 24h)
print(output[0])
```

**🌿 Livada — identificare boli cu modele specializate:**
```python
# Modele fine-tuned pe boli de plante disponibile pe Replicate
output = replicate.run(
    "google-deepmind/gemma-3-27b-it",  # sau alt model vizual
    input={
        "image": open("frunza.jpg", "rb"),
        "prompt": "Identifică boala acestei frunze de măr. Tratament."
    }
)
```

---

## 🎯 Recomandări personalizate pentru proiectele tale

### 🏢 RIS (Romanian Intelligence System)
```
Pipeline recomandat:
1. Tavily → colectare date web despre firme (1.000 req/lună gratuit)
2. Jina Reader → extragere conținut curat din pagini web (1M tokens)
3. Mistral OCR → extragere text din documente scanate (1B tokens/lună)
4. Cohere Embed 4 → vectorizare documente pentru căutare (gratuit)
5. Cohere Rerank 3.5 → precizie rezultate (gratuit)
6. DeepSeek R1 → analiză financiară complexă (5M tokens gratuit)
7. Gemini 2.5 Flash → sinteză și rapoarte (1.000 req/zi)

Cost total: $0 pentru PoC și early development
```

### 📐 Traduceri-Matematica
```
Pipeline recomandat:
1. Mistral OCR → extragere text din PDF/DOCX cu layout (1B tokens/lună)
2. Hugging Face NLLB-200 → traducere ro→sk fără pivot (1.000 req/zi)
3. Gemini 2.5 Flash → verificare calitate traducere (1.000 req/zi)
4. Claude API (al tău, plătit) → FormulaGuard + traducere finală calitate

Alternativă gratuită 100%:
Mistral OCR + NLLB-200 + Groq (verificare) = $0
```

### 🌿 Livada (Dashboard + Identificare boli)
```
Pipeline recomandat:
1. Gemini 2.5 Flash → identificare boli din poze (multimodal, 1.000 req/zi)
2. Groq Llama 70B → răspunsuri rapide la întrebări tratamente (1.000 req/zi)
3. Mistral Large → generare ghiduri detaliate tratament (1B tokens/lună)

Exemplu request complet:
- Upload poză frunză bolnavă → Gemini identifică boala
- Groq generează imediat tratamentul recomandat
- Mistral scrie ghidul complet de tratament
Cost: $0
```

### 🍰 Cake and Roll AFI
```
Pipeline recomandat:
1. Groq Llama 8B → chatbot rapid comenzi (14.400 req/zi, sub 0.5s)
2. Cloudflare FLUX → imagini menu/promo (~100 imagini/zi gratuit)
3. Groq Whisper → transcriere comenzi vocale (2.000 req/zi)
4. Gemini Flash → analiză recenzii clienți (1.000 req/zi)
Cost: $0
```

### 🏗️ ITP Hall Secusigiu
```
Pipeline recomandat:
1. Groq Whisper → transcriere note tehnice audio (2.000 req/zi)
2. Mistral Large → generare rapoarte tehnice (1B tokens/lună)
3. DeepSeek V4 → analiză documente tehnice complexe (5M tokens)
Cost: $0
```

---

## 🚀 Ghid rapid de start — primele 48 ore

### Ziua 1 — Instalează în această ordine (2-3 ore)

```bash
# 1. Google AI Studio (cel mai generos, cel mai important)
# → https://aistudio.google.com/app/apikey
# → Copiază API key în .env: GOOGLE_API_KEY=AIza...

# 2. Groq (viteză, Whisper STT)  
# → https://console.groq.com/keys
# → GROQ_API_KEY=gsk_...

# 3. Hugging Face (NLLB ro→sk)
# → https://huggingface.co/settings/tokens → New token → Read
# → HF_TOKEN=hf_...

# 4. Cohere (RAG pipeline RIS)
# → https://dashboard.cohere.com/api-keys
# → COHERE_API_KEY=co-...

# 5. Tavily (web search pentru RIS)
# → https://app.tavily.com
# → TAVILY_API_KEY=tvly-...

pip install google-generativeai groq huggingface_hub cohere tavily-python openai mistralai
```

### Ziua 2 — Verificare că funcționează totul

```python
# test_all_apis.py
import os

# 1. Google Gemini
import google.generativeai as genai
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')
print("✅ Gemini:", model.generate_content("Salut!").text[:50])

# 2. Groq
from groq import Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
r = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Salut!"}]
)
print("✅ Groq:", r.choices[0].message.content[:50])

# 3. HuggingFace NLLB
import requests
r = requests.post(
    "https://api-inference.huggingface.co/models/facebook/nllb-200-distilled-1.3B",
    headers={"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"},
    json={"inputs": "Bună ziua", "parameters": {"src_lang": "ron_Latn", "tgt_lang": "slk_Latn"}}
)
print("✅ HuggingFace NLLB:", r.json()[0]["translation_text"])

# 4. Cohere
import cohere
co = cohere.Client(os.getenv("COHERE_API_KEY"))
r = co.embed(texts=["test"], model="embed-v4", input_type="search_query")
print("✅ Cohere Embed: vector de", len(r.embeddings[0]), "dimensiuni")

# 5. Tavily
from tavily import TavilyClient
tv = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
r = tv.search("firme Arad Romania", max_results=2)
print("✅ Tavily:", r["results"][0]["title"][:50])

print("\n🎉 Toate API-urile funcționează!")
```

---

## ⚠️ Note importante și avertismente

### Date personale și confidențialitate
| Provider | Folosesc datele pentru antrenament? | Recomandare |
|---|---|---|
| Google AI Studio (free) | ✅ Da | Nu trimite date clienți ITP/personale |
| xAI Grok (data sharing) | ✅ Da (dacă optat) | Nu folosi pentru date confidențiale |
| Mistral (Experiment) | ❌ Nu | Safe pentru date business |
| DeepSeek | ✅ Da + servere China | Nu folosi pentru date sensibile |
| Groq | ❌ Nu | Safe |
| Cohere | ❌ Nu (trial key) | Safe |
| Cloudflare | ❌ Nu | Safe |

### ⚠️ DeepSeek — risc specific
Serverele sunt în China. Datele tale traversează rețeaua chineză. **Nu trimite:**
- Date personale ale clienților
- Informații financiare confidențiale
- Date legate de ITP sau documente auto

**Folosește DeepSeek pentru:** cercetare publică, cod generic, analiză date publice (ANAF public).

### Strategie buget după epuizare credite gratuite
```
Prioritate 1: Gemini (rate-limited permanent, gratuit mereu)
Prioritate 2: Groq (rate-limited permanent, gratuit mereu)  
Prioritate 3: Mistral (1B tokens/lună, gratuit mereu)
Prioritate 4: DeepSeek (cel mai ieftin: $0.28/M tokens)
Prioritate 5: Claude API (al tău, plătit, pentru calitate maximă)
```

---

## 📋 Fișier .env complet recomandat

```bash
# .env — copiază și completează cu cheile tale

# === TIER 1 — Esențiale ===
GOOGLE_API_KEY=AIza...              # aistudio.google.com/app/apikey
XAI_API_KEY=xai-...                 # console.x.ai
GROQ_API_KEY=gsk_...                # console.groq.com/keys
DEEPSEEK_API_KEY=sk-...             # platform.deepseek.com/api_keys
MISTRAL_API_KEY=...                 # console.mistral.ai/api-keys

# === TIER 2 — Foarte utile ===
OPENROUTER_API_KEY=sk-or-...        # openrouter.ai/keys
CEREBRAS_API_KEY=csk-...            # cloud.cerebras.ai
COHERE_API_KEY=co-...               # dashboard.cohere.com/api-keys
CLOUDFLARE_ACCOUNT_ID=...           # dash.cloudflare.com
CLOUDFLARE_API_TOKEN=...            # dash.cloudflare.com/profile/api-tokens
HF_TOKEN=hf_...                     # huggingface.co/settings/tokens

# === TIER 3-4 — Specializate ===
SAMBANOVA_API_KEY=...               # cloud.sambanova.ai
NVIDIA_API_KEY=nvapi-...            # build.nvidia.com
TOGETHER_API_KEY=...                # api.together.ai/settings/api-keys
FIREWORKS_API_KEY=fw_...            # fireworks.ai/account/api-keys
PERPLEXITY_API_KEY=pplx-...         # perplexity.ai/settings/api
TAVILY_API_KEY=tvly-...             # app.tavily.com
JINA_API_KEY=jina_...               # jina.ai
REPLICATE_API_TOKEN=r8_...          # replicate.com/account/api-tokens

# === Ale tale (plătite) ===
ANTHROPIC_API_KEY=sk-ant-...        # console.anthropic.com
```

---

*Generat de Claude Sonnet 4.6 | Verificat aprilie 2026*  
*Limitele se schimbă — verifică întotdeauna la provideri înainte de a planifica producție*
