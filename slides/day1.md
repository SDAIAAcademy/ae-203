---
course: "Building Applications on Language Models"
code: "AE-203"
version: "2027.2.0"
deck: "day1"
day: 1
language: "en"
view: "trainee"
source: "https://sdaiaacademy.github.io/ae-203/slides/day1.html"
---

# Building Applications on Language Models

## Day 1: Calling models well

#### [day1#title] Calling models well

*SDAIA Academy · Building Applications on Language Models*

Day 1

AI Engineering Track · 4 teaching days + capstone day · 4 sessions · 4 labs · AE-203

#### [day1#agenda] Calling models well

*Today*

- **Session 1 · Tokens, context and cost**: What a token is, why Arabic costs more of them, and what a request really sends and costs
- **Session 2 · Three API shapes, one interface**: Chat Completions, Responses and Messages side by side, one client made once for hosted and local endpoints, and a cut-off reply told from an oversized request
- **Session 3 · Prompts as versioned code**: Instructions in a versioned file with an owner, rendered safely and pinned by tests
- **Session 4 · Streaming, timeouts and retries**: Streaming and where it gets buffered, timeouts, which errors to retry, backoff with jitter, and a fallback model

#### [day1#meet-darb] Darb Transit Authority wants a rider assistant that it can test and defend

*The case study for four days*

- **The network.** Four metro lines (M1 to M4) and eight bus routes, a trip-status service and a ticket service.
- **The riders.** 300 messages in Arabic, English, Arabizi and a mix; some carry personal data or embedded instructions.
- **The rules.** 60 policies in two languages: 120 pages, one of them superseded, one carrying a planted instruction.

> **Wasil (واصل)** is the assistant you build. Ghada Al-Qahtani owns its behaviour, Mishal Al-Anazi runs operations control, Hanan Al-Shehri is the data protection officer and Ziyad Al-Amri runs the service.

### Session 1: Tokens, context and cost

#### [day1#s1] Tokens, context and cost

*Session 1*

- Count the tokens of a request, its instructions and its tool definitions
- Compare the token cost of the same text in Arabic and English
- Estimate daily cost and latency from tokens and example prices

#### [day1#what-a-token-is] A model reads and writes tokens, and you pay per token

*The unit of everything*

- A **token** is a piece of text from the model's vocabulary: a word, part of a word, a digit, a space.
- Input tokens (what you send) and output tokens (what it writes) are counted and usually priced apart.
- The **context window** is the most tokens one call can hold, input and output together.
- Each model family has its own tokenizer, so the same text has a different count on each.

- text: Was the Red Line late yesterday?
- tokens: 7 with the open Qwen3 tokenizer

#### [day1#arabic-token-tax] The same policy costs more tokens in Arabic than in English

*Measured in Lab 1.1*

| Item | Value |
| --- | --- |
| English, per 100 characters | 28.8 |
| Mixed | 38.0 |
| Arabizi | 42.1 |
| Arabic script | 43.3 |

**1.37×** tokens for the 60 policies in Arabic against the same 60 in English

- **Why it matters.** Arabic riders pay more of the budget and fill the window sooner. Measure it for the model you choose.

#### [day1#what-a-request-sends] The rider writes 22 tokens; the request carries 488

*What one request really sends*

| Item | Value |
| --- | --- |
| Tool definitions (two tools) | 406 |
| System instructions | 60 |
| The rider's message | 22 |

> **Stable first.** Instructions and tool definitions repeat on every call. Keep them identical and first, so a provider that caches a repeated prefix can reuse them.

#### [day1#cost-from-tokens] Daily cost is messages times tokens times price, per million

*From tokens to money*

```python
# file: Lab 1.1 · step 4
def daily_cost(n, tokens_in, tokens_out, price_in, price_out):
    return n * (tokens_in * price_in + tokens_out * price_out) / 1_000_000

daily_cost(10_000, 490, 60, 0.10, 0.40)    # 0.73 a day
daily_cost(10_000, 490, 60, 3.00, 15.00)   # 23.7 a day
```

> **Example prices, not a provider's.** The two price pairs are inputs to compute with. Take real ones from the pricing page on the day you decide.

#### [day1#latency-parts] Latency is the time to the first token plus the writing time

*Two clocks in every reply*

1. **Send** the request crosses the network
2. **Read** the model processes the input: time to first token
3. **Write** output tokens, one after another

- **2.1 s** per reply with 0.6 s to the first token, 60 tokens at 40 per second (assumed)
- **0.42** requests per second in the busiest hour, if 15% of 10,000 arrive then

#### [day1#choose-model-per-task] Pick the smallest model that passes your tests, task by task

*Choosing a model per task*

| Wasil's task | What it needs | A reasonable first choice |
| --- | --- | --- |
| Extract route, date, type | Follows a schema, reads Arabic and Arabizi | A small model with structured output |
| Call trip-status and tickets | Reliable tool calls | A model that supports tools well |
| Answer from policy pages | Stays inside the passages, cites them | A mid-size model, checked on Day 3 |
| Grade answers | Agrees with human labels | Validated on Day 4 before use |

> **Where data may go decides first.** Content classified above what a hosted provider may receive stays on a local model, whatever the scores.

#### [day1#checkpoint-1] Where does Wasil's token bill come from?

*Checkpoint*

**Question:** Wasil answers 10,000 short rider messages a day with two tools defined. Ghada wants to cut the input tokens. Which change cuts the most?

- A. Ask riders to write shorter messages
- B. Shorten the tool definitions and their descriptions
- C. Ask the model for shorter replies
- D. Answer every rider in English

#### [day1#lab-1-1] Tokens and cost for 10,000 messages

Lab 1.1 · 25 min

Count tokens for Arabic and English rider messages and estimate daily cost and latency for 10,000 messages, with an open tokenizer and no model call.

[D1_1_tokens_cost.ipynb](https://sdaiaacademy.github.io/ae-203/labs/D1_1_tokens_cost.ipynb)

- [ ] Count tokens per message, by language (5 min)
- [ ] The same policy in Arabic and in English (5 min)
- [ ] What one request really sends (5 min)
- [ ] Daily cost for 10,000 messages at two example prices (5 min)
- [ ] Latency per message and load in the busiest hour (5 min)
- [ ] ✱ Stretch: Arabizi against Arabic script for the same complaint

### Session 2: Three API shapes, one interface

#### [day1#s2] Three API shapes, one interface

*Session 2*

- Locate messages, tool calls and usage in each of the three API shapes
- Fill a comparison table that matches the reference
- Switch between a hosted and a local endpoint by configuration

#### [day1#three-shapes] Three API shapes carry the same conversation in different places

*Three ways to say the same thing*

- **Chat Completions.** A list of messages with roles: system, user, assistant, tool. The most widely copied shape.
- **Responses.** Instructions plus input items; the reply is a list of output items such as messages and function calls.
- **Messages.** A top-level system field; content is a list of typed blocks such as text, tool use and tool result.

> **Open Responses** is an open specification, based on the Responses shape, for one interface across providers.

#### [day1#tool-call-three-ways] The same tool call sits in three different places

*Lab 1.2 · step 1*

| Shape | Where the call is | Arguments |
| --- | --- | --- |
| Chat Completions | `choices[0].message.tool_calls` | a JSON string |
| Responses | an `output` item of type `function_call` | a JSON string |
| Messages | a `content` block of type `tool_use` | an object |

All three carry `get_trip_status(route="M1", date="2026-11-14")` for "Was the Red Line late yesterday?"

#### [day1#results-and-usage] Tool results, stop reasons and usage fields are spelled differently too

*Lab 1.2 · steps 2 and 3*

|  | Chat Completions | Responses | Messages |
| --- | --- | --- | --- |
| Tool result back | role `tool`, `tool_call_id` | `function_call_output`, `call_id` | `tool_result` block, `tool_use_id` |
| Why it stopped | `finish_reason` | `status` and item types | `stop_reason` |
| Usage | `prompt_tokens`, `completion_tokens` | `input_tokens`, `output_tokens` | `input_tokens`, `output_tokens` |

#### [day1#cut-off-or-too-big] Two short answers to the rider, two different faults in the metadata

*Reading the metadata*

```
# file: Response A · status 200
"finish_reason": "length",
"usage": {"prompt_tokens": 1240,
          "completion_tokens": 150}
# the request sent max_tokens: 150
```

```
# file: Response B · status 400
error: input of 8,350 tokens
exceeds the 8,192-token
context window
# no choices, no usage
```

Which reply was cut off by the output limit, and which request was too large for the window?

#### [day1#cut-off-what-next] A cut-off reply needs room to write; an oversized request needs a shorter input

*Read the status first, then the stop reason*

| What you read | What happened | What to do |
| --- | --- | --- |
| 200, `finish_reason` `length` (Messages: `stop_reason` `max_tokens`), output tokens equal your limit | The model wrote until your output limit: the reply is cut off | Raise the limit or ask for less; never parse a cut-off JSON reply as complete |
| 400 naming the context window; no choices, no usage | The input, and on some servers the output allowance too, is more than the window: nothing was generated | Trim the history, the passages or the tool definitions; the same request fails again |
| 200, `finish_reason` `stop` | A complete reply | Use it |

#### [day1#one-interface] Handle the shape in one place; the rest of the code never sees it

*Provider-neutral code*

```python
# file: labs/llm.py
resp = llm.complete(messages, tools=TOOLS)
# provider from LLM_PROVIDER:
#   openrouter  hosted, free models
#   local       any OpenAI-compatible server
#   scripted    offline stand-in
text = llm.text(resp)
usage = resp.usage
```

- **Your own thin client.** What the course uses: one function, a cache, a fallback list, a ledger of tokens.
- **A gateway or library.** LiteLLM and similar tools translate between providers for you, with routing and budgets.

#### [day1#connection-per-call] A new client for every call opens a new connection every time

*Before the first token*

| One complaint, three model calls | New client per call | One client, reused |
| --- | --- | --- |
| Call 1: lookup, TCP, TLS | 20 + 40 + 40 ms | 20 + 40 + 40 ms |
| Call 2 | 20 + 40 + 40 ms | reused: 0 ms |
| Call 3 | 20 + 40 + 40 ms | reused: 0 ms |
| **Set-up for the complaint** | **300 ms** | **100 ms** |

Assumed: a 40 ms round trip and a 20 ms name lookup; TCP and TLS 1.3 take one round trip each.

> **Make the client once and reuse it:** its pool keeps the connection open. `llm.client()` keeps one per provider (Lab 1.2).

#### [day1#local-endpoint] A local server that speaks the same protocol changes three settings, not your code

*Hosted or local*

| Setting | Hosted (OpenRouter) | Local server |
| --- | --- | --- |
| Base URL | `https://openrouter.ai/api/v1` | `http://127.0.0.1:8765/v1` |
| Key | from `OPENROUTER_API_KEY` | usually none |
| Model name | a free model id | whatever the server loaded |

> **Same protocol, different behaviour.** Another model, chat template and tool support: evaluate before switching.

#### [day1#free-models-change] Free models come and go and have request limits: plan for both

*Working with free hosted models*

- Free variants on OpenRouter have an id that ends in `:free` and limits per minute and per day.
- The course default and its fallbacks are settings in `labs/.env`; identical requests replay from a local cache.
- A model that disappears answers with an error: pick another free model with tool support.

#### [day1#checkpoint-2] What breaks when the provider changes?

*Checkpoint*

**Question:** Ziyad moves Wasil from a Chat Completions provider to one that serves only the Messages shape. The cost dashboard reads `usage.prompt_tokens`. What happens to it?

- A. It keeps working, since every provider reports usage
- B. It shows higher costs, since the new provider is dearer
- C. It reads the tokens from the reply's text instead
- D. It finds no such field: Messages reports input_tokens

#### [day1#lab-1-2] One request, three shapes, one client

Lab 1.2 · 25 min

Read the same request in three API shapes, fill the comparison table against the reference, and send one request to a hosted and a local endpoint through one client.

[D1_2_three_shapes.ipynb](https://sdaiaacademy.github.io/ae-203/labs/D1_2_three_shapes.ipynb)

- [ ] Read the tool call out of each shape (6 min)
- [ ] Read the usage out of each shape (6 min)
- [ ] Fill the comparison table and check it (6 min)
- [ ] The same call to a hosted and a local endpoint (7 min)
- [ ] ✱ Stretch: Send the Responses shape to a provider that serves it

### Session 3: Prompts as versioned code

#### [day1#s3] Prompts as versioned code

*Session 3*

- Separate system instructions from the rider's message
- Keep a prompt as a versioned template with an owner
- Pin a prompt's behaviour with tests before a release

#### [day1#system-and-user] Instructions come from Darb; the message comes from the rider

*Who says what*

Prompt for Wasil's request:

```text
System: You are Wasil, the rider assistant of Darb Transit Authority. Today is 2026-11-15. Never promise a refund.
User: The 27 bus was 22 minutes late yesterday. I want a refund.
```

Darb's instructions · The rider's words

- The system message holds what is true for every rider: identity, rules, the date.
- The user message holds only what this rider wrote. Never paste rider text into the instructions.

#### [day1#examples-in-prompt] One or two examples in the prompt fix the format faster than a paragraph

*Showing, not only telling*

**Example rider:** el bas 27 ta2a5ar ams

**Example reply (good example):** {"route": "B27", "date": "2026-11-14", "complaint_type": "delay"}

- **Choose hard examples.** Arabizi, Arabic-Indic digits, a date in words: the cases the model gets wrong.
- **Keep them few.** Each example is sent on every call; it is part of the stable prefix.

#### [day1#prompt-as-file] A prompt is a file with a version and an owner, not a string in the code

*Lab 1.3 · steps 1 and 2*

```
# file: artifacts/lab13/wasil.v1.md
---
name: wasil
version: 1
owner: Ghada Al-Qahtani
note: moved out of the code
---
You are Wasil, ... Today is {today}.
Introduce yourself as: "I am Wasil, ..."
If the request is not about Darb, reply: ...
```

- Under version control: every change has a diff, an author and a reason.
- Rendered with named values; a missing value stops the call.
- The owner reviews changes to behaviour, as a code owner would.

#### [day1#tests-pin-behaviour] Pin behaviour with tests that check a property, not the wording

*Lab 1.3 · step 3*

```python
# file: Lab 1.3
def test_discloses_ai(system):
    return "ai assistant" in reply_to(system, "Who are you?").lower()

def test_declines_off_topic(system):
    reply = reply_to(system, "Write me a poem about the sea.")
    return "only help with darb" in reply.lower()
```

> **Two properties Darb promised:** riders know they talk to an AI assistant, and Wasil stays on Darb business.

#### [day1#a-change-is-a-release] A friendlier rewrite failed both tests: a prompt change is a release

*Lab 1.3 · step 4*

```
# file: wasil.v1.md → wasil.v2.md
-Introduce yourself as: "I am Wasil, Darb's AI ..."
-If the request is not about Darb, reply: "I can ..."
+Be warm and helpful with anything the rider asks.
```

| Test | v1 | v2 |
| --- | --- | --- |
| Discloses AI | pass | fail |
| Declines off-topic | pass | fail |

> **Nothing in the diff looked dangerous.** The tests caught what review alone would miss.

#### [day1#prompt-release-flow] Edit, test, review, release, and keep the old version to roll back to

*The release path*

1. **Edit** a new version file
2. **Test** the pinned properties
3. **Review** by the owner
4. **Release** with a changelog line

> **Day 4 widens the tests** into a 40-case evaluation set that runs on every change of prompt, model or code.

#### [day1#checkpoint-3] Which test pins the behaviour?

*Checkpoint*

**Question:** Ghada wants a test that fails if a prompt change stops Wasil from telling riders it is an AI assistant. Which test does that and survives harmless rewording?

- A. Ask "Who are you?" and check that the reply mentions an AI assistant
- B. Ask "Who are you?" and compare the reply with a saved reply
- C. Check that the prompt file contains the word "AI"
- D. Check that the reply is under 30 words long

#### [day1#lab-1-3] Wasil's instructions as a versioned template

Lab 1.3 · 25 min

Move the assistant's instructions into a versioned template, write two tests that pin its behaviour, and watch a well-meant edit fail them.

[D1_3_prompt_versions.ipynb](https://sdaiaacademy.github.io/ae-203/labs/D1_3_prompt_versions.ipynb)

- [ ] Save the instructions with a header (5 min)
- [ ] Load and render, refusing missing variables (7 min)
- [ ] Two tests that pin its behaviour (7 min)
- [ ] A well-meant edit against the tests (6 min)
- [ ] ✱ Stretch: Pin the Arabic disclosure too

### Session 4: Streaming, timeouts and retries

#### [day1#s4] Streaming, timeouts and retries

*Session 4*

- Measure the time to first token of a streamed reply
- Retry only the errors worth retrying, with backoff
- Fall back to a second model and test every path

#### [day1#streaming] Streaming shows the first words early; the total time stays the same

*Lab 1.4 · step 1*

- **0.60 s** to the first word on the simulated endpoint
- **about 1 s** to the whole reply

- Stream to a person reading; do not stream to code that needs the whole JSON.
- A streamed reply can still fail half way: handle the cut-off end.

#### [day1#buffered-stream] The model streamed, yet the rider still waited for the whole reply

*Timing evidence*

| The same reply, timed after each hop | First byte | Last byte | Reads |
| --- | --- | --- | --- |
| Leaving the model server | 0.60 s | 1.15 s | 12 |
| After Darb's API gateway | 0.61 s | 1.16 s | 12 |
| On the rider's phone, after the edge proxy | 1.17 s | 1.17 s | 1 |

Which hop holds the reply back?

#### [day1#find-the-buffer] The first hop where first and last byte meet is the one that buffers

*Hop by hop*

- Time the first byte, the last byte and the number of reads after each hop, from the model outward.
- A hop that buffers holds every piece until the reply is complete: first byte equals last byte, in one read, while the hop before it still streams.
- Here that is the edge proxy. Turn off response buffering for the streaming route there, then time it again.

> **Change only the hop the numbers name.** If the gateway's row had already shown one read, the proxy after it would be innocent.

#### [day1#timeouts] Every model call needs a timeout shorter than the rider's patience

*Never wait forever*

- A call without a timeout ties up a worker until the provider gives up, if it ever does.
- Set it from your latency budget: Wasil's reply should start within a few seconds.
- A timeout is a failure you chose: decide what happens next, retry or fall back.

#### [day1#which-errors-retry] Retry what may pass next time; raise what will fail again

*Lab 1.4 · step 2*

| Failure | Retry? | Why |
| --- | --- | --- |
| Timeout | yes, a few times | the next attempt may be faster |
| 429 rate limited | yes, after waiting | the limit resets |
| 500, 502, 503 | yes | a busy or broken server |
| 400 bad request | no | the same request fails the same way |
| 401 bad key | no | fix the configuration |

#### [day1#backoff-jitter] Wait longer after each failure, with a little randomness

*How long to wait*

```python
# file: Lab 1.4 · call_with_retry
for attempt in range(retries + 1):
    try:
        return endpoint(prompt, timeout=timeout)
    except TimeoutError: ...
    except EndpointError as e:
        if e.status not in RETRYABLE:
            raise                      # a 400 is not retried
    time.sleep(base * 2 ** attempt + random.uniform(0, base))
```

> **Jitter** keeps clients that failed together from retrying together.

#### [day1#fallback-model] When the primary keeps failing, a fallback model answers

*Lab 1.4 · step 3*

- primary: timeout after 0.5 s
- primary: timeout after 0.5 s
- primary: timeout after 0.5 s
- fallback: called
- reply: [fallback] Route M1 is running 12 minutes late.

> **A fallback is another model.** It must pass the same tests; record which model answered each request.

#### [day1#test-the-failures] Test each failure path on purpose, with a planned slow endpoint

*Lab 1.4 · step 4*

| Test | Plan of the endpoint | Expected |
| --- | --- | --- |
| slow then ok | 0.8 s, then 0.05 s | one timeout, then the reply |
| rate limited twice | 429, 429, then 0 s | three attempts |
| fallback after server errors | 503 three times | the fallback answers |
| bad request not retried | 400 | one attempt, no fallback |

#### [day1#checkpoint-4] Retry, fall back or raise?

*Checkpoint*

**Question:** Wasil's call to the primary model answers 400: the tool schema it sent is invalid. What should the client do?

- A. Retry three times with backoff
- B. Send the same request to the fallback model
- C. Raise the error and fix the schema
- D. Return an empty reply to the rider

#### [day1#lab-1-4] Timeouts, retries and a fallback model

Lab 1.4 · 25 min

Add a timeout, a retry with backoff and a fallback model, and test them against a simulated slow endpoint.

[D1_4_retries.ipynb](https://sdaiaacademy.github.io/ae-203/labs/D1_4_retries.ipynb)

- [ ] Stream a reply and measure the time to first token (6 min)
- [ ] A retry with exponential backoff (7 min)
- [ ] A fallback model (6 min)
- [ ] Four tests against planned failures (6 min)
- [ ] ✱ Stretch: A retry budget shared by all requests

#### [day1#wrap-up] Three things to keep

*Day 1 · wrap-up*

- **Count before you choose.** Tokens per request, by language, times 10,000 a day: the price list then decides.
- **One interface.** The shape lives in one adapter; the provider is configuration.
- **Prompts and failures are code.** Versioned, owned, tested: the instructions and every failure path.

#### [day1#next] Day 2: Structured data and tools

*Next*

Rider messages become typed objects, and Wasil calls the trip-status and ticket services. Finish any open lab at home from its solution in `labs/solutions/`.
