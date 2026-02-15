## Goal
A website for preparing students for the [World Scholar's Cup](https://en.wikipedia.org/wiki/World_Scholar%27s_Cup) Regional exams by simulating wsc-style questrions. 
# High-lvel design
## Modules
* topic-material-extractor
  * extracts the material to be learned from the WSC website and transforms it into a structured representation to be used by the question-generation module
  * The entire list of topics and their linked content are [at the WSC dedicated page](https://themes.scholarscup.org/#/themes/2026/guidingquestions). The page consists of a section per topic. The page UI on the WSC website allows collapsing and expanding of each topic to view its content.
  * A topic consists of:
    * Topic title, e.g. "Progress not regress", which is the title of the second section (== topic) on the page
    * Topic contents - the contens of the section. Often a list of bullet points. 
    * Extended topic contents: links to related content (articles, youtube videos, blog posts etc. ). These appear as part of the content text and epand on a particular aspect
    * Terminology: bullet points which contain a list of terms separated by a pipe sign. Example: Gross Domestic Product | Gross National Income | Gini Coefficient. Each such term is part of the topic material and it is required to know the essential facts concerning it, even if it these are not explicitly supplied in the text. Sometimes the term is a link leading to a page where the required material about the term does exist. When it is not a link, knowledge about this term still needs to be consumed, e.g. from Wikipedia.
    * Works of art: paintings/photo/video/sound etc. Appear in the material as a bullet point consisting of the name of the artist and the name of the work separated by a pipe sign. E.g. Albrecht Dürer | The Four Horsemen of the Apocalypse (1498). The work is usually a link to the actual piece (image, video, poem etc). The required knowledge in these cases is: 1. acquaintance with the artwork 2. Given the name of the artwork -> the name of the creator 3. Given the name of the creator and some context about the work -> the name of the work
  * The extractor needs to round up all the relevant content for each of the topics. This includes per topic:
    * The topic text from the topic section on the WSC site
    * Summaries of the info in the extended topic contents links. For this, the 
    * A list of topic terms and a summary about each
    * A list of topic related artworks and a summary about each. The summary should include: description of the work, historical context and interpretation
* question-generation: 
  * Uses the material extracted by the topic-material extractor in order to generate wsc-style questions according to the question structure guidelines described in question-structure-guideliens.md
* UI
  * User interaction with questions: topic selection, answering, skipping etc.
  * a reference implementation can be found in reference-impl.html in this project. This used to be an old version fo the question generation site. 

# Modile Design
## UI
* A static website, pure html. If JS is absolutly required it may be added, but prefer html+css solutions, unless this introduces substantial complexity which can be avoided with JS.
* index.html contains the UI
* questions.jsonl is the question store
* UI functionality:
    * Topic selection sidebar: multiple selection from a list of topics + "Ask me" button
    * When "Ask me" is clicked, questions start being displayed one at at time. Questions are centered at the top of the middle of the screen
    * User interaction with a question - as in the reference implementation

## topic-material-extractor
* All material per topic is persisted in a "topic-name" folder under a "topics". 
### open issues
* how to persist the material: json? md? single file? file per article? what are the tradefoffs? 

## question-generation
* questions are stored as jsonl in question-pool.jsonl
* each question jsonl adheres to the schema described in wsc-question.schema.json
* the name of the questions file is a meaningful name which describes the dataset
