# The writing standard: ASD-STE100 Simplified Technical English

Use these rules for the `README.md` of dietverse and for this file. Section 3 gives the project
vocabulary. Each term in Section 3 has one meaning in all of the documentation.

## 1. The writing rules

### Words

1. Use one word for one meaning, and one meaning for one word. Do not use synonyms for variety.
2. Use a word only as one part of speech. For example, `test` is a noun or a verb, `check` is a verb.
3. Do not use phrasal verbs (`set up`, `carry out`, `find out`, `pick up`, `look up`, `come up with`).
   Use one verb: `prepare`, `do`, `find`, `get`, `make`.
4. Do not use an `-ing` form as a noun or an adjective (`the running job`, `after indexing`).
   Exception: a technical name, a file name, a command or a status value.
5. Do not use contractions (`don't`, `it's`, `can't`). Do not use slang or idioms
   (`out of the box`, `under the hood`, `at a glance`, `gotcha`, `bells and whistles`).
6. Do not use `and/or`. Write `A, B or both`.
7. Do not use `should`, `could`, `would` or `may` for instructions. Use `must` for a rule, the
   imperative for a step and `can` for a possibility.
8. Keep the articles `a`, `an` and `the` in sentences.
9. Do not make a noun cluster of more than three words. A technical name is one word.

### Sentences

1. A procedural sentence (an instruction) has a maximum of **20 words**.
2. A descriptive sentence has a maximum of **25 words**.
3. Write one instruction in one sentence.
4. Use the imperative for an instruction: `Run the tests.` Not `The tests should be run.`
5. Use the active voice. Use the passive voice only when the agent of the action is not important.
6. Use only the simple present, the simple past and the simple future.
7. Put a condition before the instruction: `If the index is stale, build it again.`
8. Do not use semicolons in sentences. Write two sentences.

### Paragraphs, notes and warnings

1. A paragraph has one topic and a maximum of **6 sentences**. Start with the topic sentence.
2. A warning or a caution starts with a clear command. Then it gives the reason.
3. A note gives information. It does not give an instruction.
4. Use a vertical list for a sequence or a set of conditions. Each item of a numbered procedure is one step.

### Tables, headings and diagrams

1. A table cell can be a short phrase. If a cell has a sentence, the sentence obeys the rules.
2. A heading is a noun phrase (`The cost model`) or an imperative (`Run the demo`).
   Do not start a heading with an `-ing` form.
3. A diagram label is a short phrase. Use the same terms as the text.

### What STE does not change

Code, commands, file names, paths, field names, environment variables, status values, enum values,
product names and URLs stay exactly as they are. They are technical names. Put them in backticks.

## 2. General words to replace

| Do not use | Use |
|---|---|
| utilize, leverage | use |
| in order to | to |
| set up | prepare, install, configure |
| carry out, perform | do |
| make sure, ensure | make sure (allowed), or `check that` |
| a lot of, lots of | many, much |
| e.g., i.e. | for example, that is |
| should (instruction) | must (rule) / imperative (step) |
| might, may (possibility) | can |
| very, really, just, simply, easily | (delete) |
| seamless, robust, powerful, blazing | (delete or give a measured fact) |

## 3. Project vocabulary

These terms have one meaning in the dietverse documentation. The code names are in backticks.

### 3.1 Technical names (nouns)

| Term | Meaning | Do not use |
|---|---|---|
| **country data** | The four CSV files of the COVID-19 Healthy Diet data set. | dataset (alone), archive |
| **measure** | One of the four files: `energy`, `quantity`, `fat`, `protein`. | metric (for a file), table |
| **food group** | One of the 21 detailed FAO groups, for example `Pulses`. | category, food type |
| **aggregate** | `Animal Products` or `Vegetal Products`. | total group |
| **supply share** | The share of a national supply that one food group gives, in %. The groups of a country add up to 100%. | intake, consumption, recommendation |
| **outcome** | A country value: `deaths_per_100k`, `obesity_pct` or `cfr_pct`. | result, endpoint |
| **CFR** | Case-fatality ratio: deaths divided by confirmed cases. It depends on testing. | mortality (alone), death rate |
| **control** | A country variable that the partial correlation removes, for example `median_age`. | confounder (in prose), covariate (in prose) |
| **partial correlation** | The Spearman correlation after a linear fit of the ranks on the ranks of the controls. | adjusted effect |
| **ecological association** | An association between country values. It does not apply to persons. | effect, risk |
| **profile** | The data of one adult: age, sex, weight, height, activity, goal, diet, allergies, intolerances, conditions, pregnancy, country. | form, user data |
| **energy target** | The daily energy from the Mifflin-St Jeor equation, the activity factor and the goal. | calorie budget, needs |
| **pattern level** | The energy level of the food pattern table that is nearest to the energy target. | calorie level (alone) |
| **group target** | The daily amount of one pattern food group, in cup-eq, oz-eq or g. | portion, serving |
| **example food** | A food of a pattern group that the diet, the allergies and the intolerances allow. | suggestion |
| **diet guide** | The output for one profile: BMI, energy, pattern level, group targets, limits and notes. | diet plan (in prose), recommendation |
| **referral** | The status of a diet guide that tells the person to ask a professional, with no targets. | rejection |
| **country context** | The top supply shares of the country of the profile. It is not a target. | country plan |
| **screener** | The PHQ-2 and GAD-2 questions and their scores. | quiz, test, diagnosis |
| **positive screen** | A PHQ-2 or GAD-2 total of 3 or more. | diagnosis, result |
| **assistant** | The chat component of the backend. | bot, NPC, agent |
| **brain** | The text source of the assistant: the offline FAQ or an OpenAI-compatible endpoint. | model (alone), engine |
| **session** | One conversation of the assistant, kept on the backend under a random id. | chat (as a noun) |
| **turn** | One user message and one assistant answer. | exchange |
| **speech provider** | The text-to-speech component: `none`, `offline` or `polly`. | voice engine, TTS (in prose) |
| **backend** | The FastAPI app that the VR client and other clients call. | server (alone), proxy |
| **VR client** | The Unity script `BackendClient.cs`. It calls only the backend. | headset app, game |

### 3.2 Technical verbs

| Verb | Meaning |
|---|---|
| **load** | Read and check the four files of the country data. |
| **normalize** | Divide each food group by the group sum of the row and multiply by 100. |
| **control** | Remove the rank effect of a control variable before the correlation. |
| **screen** | Score the PHQ-2 and GAD-2 answers. |
| **synthesize** | Make an audio file from an answer. |
| **refer** | Tell the person to ask a doctor, a dietitian or a mental health professional. |
