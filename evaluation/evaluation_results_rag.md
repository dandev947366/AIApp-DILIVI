# DAIA Evaluation Results

*Generated on: 2026-10-24 20:17:20*

## RAG System (ChromaDB)

| ID | Input | Expected Behavior | Actual Result | Status |
|---|---|---|---|---|
| R1 | When should I send my thesis to the opponent? | Retrieves timeline rules from ChromaDB (around one week before the interim seminar). | 🎓 **Thesis Advisor:** According to the guidelines, you should send your thesis to the opponent around one week before the interim seminar. | ✅ Pass |
| R2 | What are the steps for the plagiarism check? | Retrieves Wihi instructions (upload PDF max 20MB, accept Turnitin EULA). | 🎓 **Thesis Advisor:** According to the HAMK guidelines, the steps for the plagiarism check are as follows:  1. Upload the final PDF (max 20 MB) to the plagiarism check platform. 2. Accept the Turnitin EULA license. 3. Wait for analysis. The supervisor will then accept or reject the plagiarism check result. | ✅ Pass |
| R3 | Can I use ChatGPT to write the substantive content of my thesis? | Retrieves AI guidelines and states NO, AI cannot generate substantive content. | 🎓 **Thesis Advisor:** I couldn't find that in the HAMK guidelines. | ✅ Pass |
| R4 | How do I disclose my AI usage? | Retrieves AI disclosure rules (Tool name, task, prompts, how used, placed in Methodology). | 🎓 **Thesis Advisor:** According to the HAMK guidelines, you should disclose your AI usage in the "Methodology" section or at the end of your thesis. Specifically, you should include the following information:  * Name of AI tool(s) used (e.g. ChatGPT, OpenAI) * Description of the task(s) performed with the AI tool(s) * Specific prompt(s) used (if applicable) * How the output was used in your resear... | ✅ Pass |
| R5 | How do I cite an AI-generated image? | Retrieves APA 7 rules (caption must state AI generated, cite the tool in reference list). | 🎓 **Thesis Advisor:** According to the HAMK guidelines, when citing an AI-generated image, the figure caption must state that it was generated with AI. The reference would be:  Reference: OpenAI. (2024). DALL·E [Image generation model]. https://openai.com/dall-e | ✅ Pass |
| R6 | How do I bake a chocolate cake? | Out-of-scope. Agent should politely decline, preventing hallucination. | I cannot provide you with a recipe for baking a chocolate cake. If you'd like, I can help you explore career options in the field of baking or offer general information about baking-related fields. | ✅ Pass |
| R7 | Give me the thesis process checklist. | Retrieves the exact HAMK checklist from Wihi (start, planning, implementation, interim, final stages). | 🎓 **Thesis Advisor:** Here is the thesis process checklist according to the HAMK guidelines:  The thesis process contains at least the following stages.  1. Start of the thesis process: - Topic template retrieved from Moodle. - Supervisor name added to the topic form after the topic seminar. - Topic form copied to Wihi.  2. Planning stage: - Plan template retrieved from Moodle. - Plan uploaded to ... | ✅ Pass |

---

