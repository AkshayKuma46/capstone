# Requirements Document

## Introduction

The AI Wardrobe Stylist & Recommendation Engine is a web-based system that helps users discover and plan outfits from their personal wardrobe. The user uploads photos of their garments — a pretrained vision model extracts clothing attributes (type, color, fabric, pattern, fit) from each photo and catalogs them into a wardrobe database. When the user selects an occasion, the system generates outfit combinations from their wardrobe, scores each combination using an XGBoost model grounded in a structured fashion rule corpus, and presents the top-ranked outfits as visual cards with explanations written by an LLM stylist.

The system is not a chatbot. The user interacts through structured inputs — photo uploads, occasion selectors, and outfit cards — not free-form conversation. The LLM is used only to generate natural-language explanations for why a scored outfit was recommended.

The build is organized into four sequential phases:
1. **Data Acquisition** — clean and normalize raw fashion book text
2. **Knowledge Extraction** — LLM (e.g., Gemini) extracts structured styling rules into the Rule Corpus
3. **Structured Representation** — rules compiled into a versioned JSON Rule Corpus consumed by XGBoost
4. **Predictive Integration** — XGBoost scores outfit combinations; vector embeddings power rule retrieval

---

## Architecture

```
User uploads garment photo
         │
         ▼
Pretrained Vision Model
(Gemini Vision / CLIP)
         │
         ▼
Clothing Type + Attributes
(color, fabric, category, pattern, fit)
         │
         ▼
Wardrobe Database
(garment catalog per user)
         │
         ▼
User selects occasion
         │
         ▼
Recommendation Engine
  ├── Vector Store retrieves relevant rules
  ├── XGBoost Outfit Scorer (Rule Corpus features)
  └── LLM writes explanation for each scored outfit
         │
         ▼
Ranked Outfit Cards
(score + garment images + explanation)
```

---

## Glossary

- **Vision Model**: The pretrained model (e.g., Gemini Vision, CLIP) that processes a garment photo and outputs structured clothing attributes. Not trained by this system — called as an external API.
- **Garment**: A single clothing item extracted from a photo and stored in the Wardrobe (e.g., navy blazer, white linen shirt).
- **Wardrobe**: The collection of Garments a user has catalogued in the system.
- **Outfit**: An ordered combination of two or more Garments assembled for a specific occasion.
- **Occasion**: A labeled context for outfit selection (e.g., casual, formal, business casual, outdoor, sport).
- **Rule_Corpus**: The versioned JSON knowledge base containing all styling rules extracted from fashion literature. Feeds the Outfit_Scorer as feature data.
- **Knowledge_Extractor**: The offline LLM pipeline that reads cleaned fashion book text and produces structured rules for the Rule Corpus. Runs as an admin operation, not at inference time.
- **Outfit_Scorer**: The XGBoost model that takes a feature vector representing an Outfit and outputs a compatibility score (0–100) and a Confidence_Score (0–1).
- **Vector_Store**: The vector database holding embeddings of Garments and Rule Corpus rules. Used to retrieve relevant rules for a given occasion or garment combination.
- **RAG_Pipeline**: Retrieval-Augmented Generation pipeline — retrieves the most relevant rules and garments from the Vector_Store and passes them as context to the LLM Stylist.
- **LLM_Stylist**: The LLM (e.g., Gemini) that receives a scored outfit + retrieved rules and writes a natural-language explanation for the outfit card. Does not generate outfit combinations — the Outfit_Scorer does that.
- **Outfit_Card**: The UI component that displays a recommended outfit: garment images, compatibility score, and LLM-written explanation.
- **Recommendation_Display**: The page or panel that shows the top-ranked Outfit Cards after scoring.
- **Color_Compatibility_Score**: Numeric sub-score (0–100) for how well the outfit's colors harmonize.
- **Fabric_Compatibility_Score**: Numeric sub-score (0–100) for how well the outfit's fabric types pair.
- **Confidence_Score**: Numeric value (0–1) returned alongside each Outfit_Scorer score indicating prediction reliability.
- **Admin**: User role with permission to trigger Rule Corpus updates and model retraining.

---

## Requirements

### Requirement 1: Garment Cataloguing via Vision Model

**User Story:** As a user, I want to photograph my garments and have them automatically catalogued, so that I don't have to manually enter clothing attributes.

#### Acceptance Criteria

1. WHEN a user uploads a garment photo (JPEG or PNG, up to 5 MB), THE system SHALL pass the image to the Vision Model and extract at minimum: garment category, primary color, secondary color, fabric type, pattern type, and fit type.
2. THE Vision Model extraction SHALL complete and return structured attributes within 5 seconds of image upload.
3. WHEN the Vision Model returns attributes, THE system SHALL display the extracted attributes to the user for review before saving.
4. THE user SHALL be able to edit any extracted attribute before confirming the garment entry.
5. IF the Vision Model returns a Confidence_Score below 0.6 for any attribute, THE system SHALL highlight that attribute and prompt the user to verify or correct it.
6. WHEN the user confirms the garment entry, THE Wardrobe SHALL persist the Garment and return a confirmation within 2 seconds.
7. IF an uploaded image exceeds 5 MB or is not JPEG or PNG, THEN THE system SHALL reject the upload and return an error message specifying the constraint violated.
8. THE Wardrobe SHALL enforce that a Garment name is between 1 and 100 characters.
9. THE user SHALL be able to assign occasion tags to each Garment from a predefined list that includes at minimum: casual, formal, business casual, outdoor, and sport.
10. THE user SHALL be able to add, edit, and delete Garments from their Wardrobe at any time without re-uploading a photo.

---

### Requirement 2: Wardrobe Management

**User Story:** As a user, I want to view and manage my catalogued garments, so that my wardrobe database stays accurate and up to date.

#### Acceptance Criteria

1. THE system SHALL display all Garments in the user's Wardrobe as a browsable grid, showing the garment image (if available), name, category, and primary color.
2. WHEN a user updates an existing Garment's attributes, THE system SHALL apply the changes and update the corresponding Vector_Store embedding within 10 seconds.
3. WHEN a user deletes a Garment, THE system SHALL remove the Garment record, its image, and its Vector_Store embedding.
4. THE Wardrobe SHALL support filtering Garments by category, color, fabric, and occasion tag.
5. IF the Wardrobe contains zero Garments when outfit recommendation is requested, THEN THE system SHALL show an empty-state prompt directing the user to upload garments first, and SHALL NOT invoke the Outfit_Scorer or LLM_Stylist.

---

### Requirement 3: Fashion Knowledge Extraction (Offline / Admin)

**User Story:** As an Admin, I want the system to extract styling rules from fashion book text and compile them into the Rule Corpus, so that the Outfit_Scorer is grounded in authoritative fashion knowledge.

#### Acceptance Criteria

1. WHEN an Admin uploads a cleaned fashion text document (plain-text UTF-8, up to 10 MB), THE Knowledge_Extractor SHALL parse the document and produce structured styling rules in JSON format conforming to the Rule Corpus schema.
2. THE Knowledge_Extractor SHALL extract at minimum one rule of each type: color pairing, fabric compatibility, occasion-appropriateness, and layering/proportion.
3. WHEN extraction is complete, THE Knowledge_Extractor SHALL output a versioned Rule Corpus file with a semantic version number and an ISO 8601 timestamp.
4. IF the Knowledge_Extractor encounters text it cannot map to a rule type, THEN it SHALL log the passage with a confidence score below 0.5 to an extraction log accessible to the Admin, and continue processing the remainder of the document.
5. THE Rule Corpus SHALL be parseable as valid JSON according to the published Rule Corpus schema.
6. THE Knowledge_Extractor SHALL guarantee round-trip property: parsing → serializing → parsing a valid Rule Corpus produces an equivalent object (identical rule count, type distribution, and field values).
7. WHEN a new Rule Corpus version is produced, THE Knowledge_Extractor SHALL notify the Admin with version number, rule count, and extraction timestamp.
8. IF the uploaded document is unreadable, non-UTF-8, or structurally malformed, THEN THE Knowledge_Extractor SHALL reject the file, return an error identifying the failure reason, and SHALL NOT produce a partial output.

---

### Requirement 4: Outfit Scoring with XGBoost

**User Story:** As a user, I want outfit combinations from my wardrobe to be scored for stylistic compatibility, so that I receive ranked recommendations grounded in fashion rules rather than arbitrary suggestions.

#### Acceptance Criteria

1. WHEN the user selects an occasion, THE Outfit_Scorer SHALL generate candidate outfit combinations from the user's Wardrobe and score each combination using features derived from the active Rule Corpus.
2. THE Outfit_Scorer SHALL compute a compatibility score between 0 and 100 for each candidate outfit.
3. THE Outfit_Scorer SHALL incorporate at minimum the following feature sub-scores: Color_Compatibility_Score (0–100), Fabric_Compatibility_Score (0–100), occasion match (0–100), and garment category balance (0–100).
4. THE Outfit_Scorer SHALL return a Confidence_Score between 0 and 1 alongside each compatibility score.
5. IF the Confidence_Score for an outfit is below 0.6, THE Recommendation_Display SHALL show a low-confidence indicator on that outfit card and display the actual Confidence_Score value.
6. THE Outfit_Scorer SHALL present only the top 3 highest-scoring outfits to the Recommendation_Display.
7. THE Outfit_Scorer SHALL preserve scoring monotonicity: an outfit satisfying more styling rules SHALL receive an equal or higher score than one satisfying fewer rules.
8. WHEN the active Rule Corpus version is updated, THE Outfit_Scorer SHALL invalidate cached scores and recompute on next request.
9. IF any required feature sub-score cannot be computed, THE Outfit_Scorer SHALL return a score of -1 and Confidence_Score of 0, and SHALL NOT return a partial score.
10. WHEN an Admin triggers retraining with a new Rule Corpus version, THE Outfit_Scorer SHALL complete retraining and become active within 30 minutes on standard hardware (8 GB RAM, 4 CPU cores).

---

### Requirement 5: Rule Retrieval via Vector Store

**User Story:** As the system, I need to retrieve the most relevant styling rules for a given outfit combination and occasion, so that the Outfit_Scorer operates on pertinent knowledge and the LLM_Stylist receives grounded context.

#### Acceptance Criteria

1. THE Vector_Store SHALL store embeddings for each Garment in the user's Wardrobe and for each rule in the active Rule Corpus.
2. WHEN the Recommendation Engine processes an occasion request, THE Vector_Store SHALL retrieve the top-K (default K=5, valid range 1–20) most semantically relevant rules within 1 second.
3. WHEN a Garment is added, updated, or deleted, THE Vector_Store SHALL update the affected embedding within 10 seconds; IF the update fails, THE Vector_Store SHALL log the failure with a timestamp and garment ID and return an error to the caller.
4. WHEN a new Rule Corpus version is activated, THE Vector_Store SHALL re-embed all rules within 5 minutes; failures SHALL be logged per rule identifier and at least 90% of rules must be successfully embedded.
5. IF the Vector_Store retrieval returns fewer than 3 results above similarity threshold 0.7, THE system SHALL fall back to top-3 by raw similarity score and set `low_confidence: true` in the context passed to the LLM_Stylist.
6. IF retrieval returns zero results, THE system SHALL proceed using only the base Rule Corpus without vector-retrieved context, and SHALL log the zero-result event.

---

### Requirement 6: Outfit Recommendation Display

**User Story:** As a user, I want to see my top outfit recommendations presented as clear visual cards with scores and explanations, so that I can make an informed choice about what to wear.

#### Acceptance Criteria

1. THE Recommendation_Display SHALL show the top 3 scored outfits as Outfit Cards.
2. EACH Outfit Card SHALL display: the garment images (where available), garment names, overall compatibility score (integer 0–100), and an LLM-generated explanation of 20–100 words referencing at least one styling rule.
3. WHERE a Garment has an associated image, THE Outfit Card SHALL display that image alongside the garment name.
4. THE Outfit Card SHALL display a low-confidence indicator when the Outfit_Scorer Confidence_Score is below 0.6, showing the actual value.
5. THE user SHALL be able to save any recommended Outfit to a named collection from the Outfit Card.
6. Collection names SHALL be between 1 and 50 characters; invalid names SHALL produce an inline validation error.
7. WHEN a save succeeds, THE system SHALL display a confirmation within 2 seconds; IF the save fails, THE system SHALL display an error message.
8. THE Recommendation_Display SHALL be responsive and usable on viewport widths from 320 px to 1920 px.

---

### Requirement 7: LLM Outfit Explanation

**User Story:** As a user, I want each recommended outfit to come with a clear explanation of why it works, so that I understand the styling logic and can learn from it.

#### Acceptance Criteria

1. WHEN the Outfit_Scorer produces a scored outfit, THE LLM_Stylist SHALL receive the outfit's garment list, compatibility score, Confidence_Score, occasion, and retrieved rules as context.
2. THE LLM_Stylist SHALL generate an explanation of 20–100 words for each outfit, referencing at least one specific styling rule (e.g., color harmony, occasion match, fabric compatibility).
3. THE LLM_Stylist SHALL NOT generate outfit combinations — it receives the combination from the Outfit_Scorer and only writes the explanation.
4. THE LLM_Stylist SHALL complete explanation generation within 5 seconds per outfit under normal load.
5. IF the LLM service is unavailable, THE system SHALL display the Outfit Card with score and garments but without an explanation, and SHALL show a notice that explanation generation is temporarily unavailable.
6. THE LLM_Stylist SHALL NOT reference internal model parameters, confidence thresholds, or system component names in the explanation text shown to the user.

---

### Requirement 8: Data Acquisition and Text Preprocessing (Offline / Admin)

**User Story:** As an Admin, I want raw fashion book text cleaned and normalized before knowledge extraction, so that the Knowledge_Extractor receives high-quality input and produces accurate rules.

#### Acceptance Criteria

1. WHEN an Admin uploads a raw text document (plain text or PDF), THE Data_Preprocessor SHALL remove non-semantic formatting characters (Unicode Cc and Cf categories, excluding tab U+0009 and newline U+000A); for PDFs it SHALL additionally strip headers, footers, and page numbers.
2. THE Data_Preprocessor SHALL normalize Unicode to NFC form and convert smart quotes and en/em dashes to ASCII equivalents.
3. WHEN preprocessing is complete, THE Data_Preprocessor SHALL output a cleaned plain-text file and a preprocessing report listing characters removed and normalization operations applied.
4. IF the uploaded document exceeds 10 MB, THE Data_Preprocessor SHALL reject it and return an error specifying the size limit.
5. IF the document contains fewer than 500 words after preprocessing, THE Data_Preprocessor SHALL warn the Admin that it may be too short for meaningful rule extraction.
6. THE Data_Preprocessor SHALL accept .txt and .pdf formats only; unsupported formats SHALL be rejected with an identifying error.
7. IF an uploaded PDF is unreadable, corrupted, or password-protected, THE Data_Preprocessor SHALL reject it, return an error identifying the failure reason, and SHALL NOT produce partial output.

---

### Requirement 9: System Reliability and Error Handling

**User Story:** As a user, I want the system to handle errors gracefully so that a failure in one component does not break the whole experience.

#### Acceptance Criteria

1. IF the Vision Model service is unavailable, THE system SHALL display an error on the upload screen and allow the user to enter garment attributes manually.
2. IF the LLM_Stylist service is unavailable, THE system SHALL display Outfit Cards with scores and garments but without explanations, with a notice to the user.
3. IF the Outfit_Scorer fails to score an outfit, THE system SHALL exclude that outfit from results and proceed with the remaining scored outfits; if no outfits can be scored, THE system SHALL display an error and suggest the user try again.
4. IF the Vector_Store is unavailable, THE system SHALL proceed using only the base Rule Corpus without retrieved context and SHALL log the failure.
5. WHEN any error occurs, THE system SHALL log it with severity level, timestamp, request identifier, and error message to a persistent log store.
6. WHEN an unexpected error occurs during a user-facing request, THE system SHALL return a user-friendly error message that does not expose internal component names, stack traces, or model parameters, along with a unique request identifier for support.
