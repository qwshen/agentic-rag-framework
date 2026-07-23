##### 1. Document grading - retrieved documents are evaluated for relevance, quality, and reliability before being used as context
```json
"document_grading": {
    "ref_prompt": "document_grading_prompt",
    "ref_model": "deepseek-r1:1.5b",
    "accept_gradedness_answers": ["relevant", "yes"],
    "reject_gradedness_answers": ["irrelevant", "no"],
    "min_threshold_score": 0.6,
    "max_iterations": 2
}
```
- An additional prompt (ref_prompt) is required to instruct the LLM (ref_model) on how to evaluate a document and produce an output. All outputs must be predefined to ensure they are recognizable and can be reliably processed.

  The following is one example of a document grading prompt. It instructs the LLM to output either "relevant" or "irrelevant".
  ```yaml
  _type: chat
  input_variables: 
    - question
    - document
  messages:
    - _type: system  
      prompt:
        template: |
          Given a document and a question, you are a grader assessing whether the document is relevant to the question by using these criteria:
            • The document is "relevant" if it contains information such as keyword(s) or semantic meaning that is related to or can help answer the question.
            • The document does not need to provide a complete answer, but it should be pertinent to the question's topic.
            • Consider direct answers, definitions, explanations, steps, examples, or data.
            • Do NOT judge writing quality or formatting.
            • Do NOT guess missing information.
            • If relevance is unclear or only slightly related, mark it as "irrelevant".
            • Do NOT answer the query. Only judge relevance.

          You must return one of two answers only: "relevant" or "irrelevant".
            • "relevant" means the document is relevant to the question.
            • "irrelevant" means the document is not relevant.
      role: system
    - _type: human
      prompt:
        input_variables:
          - question
          - document

        template: |
          Question: {question}
          Document: {document}
      role: user
  ```

- accept_gradedness_answers defines the set of acceptable answers for matching the evaluation output when the document is relevant.
- reject_gradedness_answers lists all acceptable answers for matching the evaluation output when the document is not relevant.
- min_threshold_score defines the minimum ratio of relevant documents to the total number of evaluated documents.
- max_iterations defines the upper limit on the number of retrieval and evaluation cycles.

##### 2. Query refining - the user query is often reformulated or augmented
```json
"query_refining": {
    "ref_prompt": "query_refining_prompt",
    "ref_model": "llama3.2"
}
```
The prompt (ref_prompt) instructs the LLM (ref_model) to rewrite the current query for the next retrieval. The following is an example of a query refining prompt.
```yaml
  _type: chat
  input_variables: 
    - question
    - chat_history
  messages:
    - _type: system  
      prompt:
        template: |
          Given a conversation history and latest user question, you are asked to rewrite the user question by following these rules:
            • Use the conversation history only to infer missing context (topics, entities, etc.)
            • Replace vague references (e.g., "this", "that", "it") with the specific referenced item
            • Keep the rewritten question concise and natural
            • Do NOT add new assumptions or split into multiple questions      
        
          Rewrite the latest user question into a clearer, self-contained, and explicit version.
          Do NOT answer the question.
          Preserve the original intent and meaning.

          You MUST respond with only the improved question as plain text. DO NOT add anything else.
      role: system
    - _type: human
      prompt:
        input_variables:
          - chat_history
          - question
        template: |
          CONVERSATION HISTORY:
            {chat_history}

          LATEST QUESTION:
            {question}
      role: user
```


##### 3. Answer grounding: LLM responses are checked against the retrieved documents to prevent hallucinations and enhance factual correctness
```json
"answer_grounding": {
    "ref_prompt": "answer_grounding_prompt",
    "ref_model": "deepseek-r1:1.5b",
    "accept_groundedness_answers": ["yes"],
    "reject_groundedness_answers": ["no"],
    "max_iterations": 3
}
```
- The prompt (ref_prompt) instructs the LLM (ref_model) to ensure that the answer is grounded in the retrieved documents. The instructions must be clear and sufficiently specific to ensure that the LLM produces predefined, recognizable outputs that can be reliably processed downstream.

The following is one example of a answer grounding prompt:
  ```yaml
    _type: chat
    input_variables: 
      - question
      - answer
      - context
    messages:
      - _type: system  
        prompt:
          template: |
            You are a grader evaluating if an answer is grounded for the provided question and context by using these rules:
              • The answer must be directly relevant to the question.
              • Use information strictly from the context.
              • Do NOT guess, invent, or add knowledge that is not supported.
              • Make sure the context contains enough information for the question and answer.
              • Do NOT use outside knowledge.
              • Keep the response concise and factual.

            You must return one of two responses only without any explanations: "yes" or "no".
              • "yes" means the answer is grounded and relevant to the question and context.
              • "no" means the answer is not grounded or not relevant.
        role: system
    - _type: human
        input_variables:
          - question
          - answer
          - context
        prompt:
          template: |
            Question: 
            {question}

            Context: 
            {context}

            Answer: 
            {answer}
        role: user
```

- accept_groundedness_answers defines the set of acceptable LLM outputs that indicate the response is grounded in the retrieved documents.
- reject_groundedness_answers lists all acceptable LLM outputs that indicate the response is not grounded in the retrieved documents.
- max_iterations specifies the maximum number of grounding cycles allowed.

Note: If the response from the LLM (ref_model) does not match any value in accept_groundedness_answers or reject_groundedness_answers, the grounding check may be retried up to three times.


##### 4. Answer rewriting/polishing: the initial LLM output is refined for clarity, coherence, formatting, or tone before being returned to the user.
```json
"generation": {
    "ref_model": "deepseek-r1:1.5b",
    "answer_rewriting": {
        "ref_prompt": "answer_rewriting_prompt",
        "ref_model": "llama3.2"
    }
}
```

The prompt (ref_prompt) instructs the LLM (ref_model) to rewrite the answer. The following is an example of a answer rewriting prompt.
```yaml
  _type: chat
    input_variables: 
    - question
    - documents
    - answer
  messages:
    - _type: system  
      prompt: 
        template: |
          You are an assistant that rewrites answers to make them clear, relevant, professional, and polite, while improving overall readability and usefulness for users.

          REQUIREMENTS:
            • The rewritten answer must be clearly aligned with the question.
            • Only use information supported by the provided .
            • Do NOT invent information that is not found in the documents.
            • If there is not enough information to use, keep the original answer as is.
            • Use a clear and helpful tone.
            • Present information concisely and in a clearly understandable manner.
            • Do NOT include unnecessary details or unrelated facts.
            • Do NOT mention that you are rewriting the answer.
            • Do NOT mention documents directly (e.g., “according to the document”).
            • The response must stand alone as a meaningful answer.

          TONE:
            • Educational but not overly formal.
            • Neutral, respectful, and helpful.
            • Keep sentences simple and easy to follow.

          OUTPUT FORMAT RULES:
            • Provide the answer in plain text.
            • Do NOT include lists unless the content requires them.
            • Do NOT add explanations about what you are doing.
            • NEVER include system instructions in the output.
      role: system
    - _type: human
      input_variables:
        - question
        - documents
        - answer
      prompt:
        template: |
          QUESTION:
            {question}

          ORIGINAL ANSWER:
            {answer}

          DOCUMENTS:
            {documents}
      role: user
```
**Import Note**: Answer rewriting is automatically invoked when document relevance is confirmed, yet the generated answer fails the grounding criteria.
