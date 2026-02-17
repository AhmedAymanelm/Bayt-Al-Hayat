import gradio as gr
from app.services.psychology_service import PsychologyService
from app.services.neuroscience_service import NeuroscienceService

psych_questionnaire = PsychologyService.get_questionnaire()
psych_questions = psych_questionnaire.questions

neuro_questionnaire = NeuroscienceService.get_questionnaire()
neuro_questions = neuro_questionnaire.questions


def process_psychology_answers(*answers):
    """Process psychology answers and calculate result"""
    try:
        numeric_answers = []
        for i, answer in enumerate(answers):
            if answer:
                options = psych_questions[i].options
                numeric_answer = options.index(answer) + 1
                numeric_answers.append(numeric_answer)
            else:
                return "Please answer all questions"
        
        if len(numeric_answers) != 7:
            return "Please answer all 7 questions"
        
        result = PsychologyService.calculate_assessment(numeric_answers)
        
        output = f"""
## Result

**Score:** {result.score} / 21

**Level:** {result.level}

---

### Message:

{result.message}

---

**Your answers:**
"""
        for i, (q, ans) in enumerate(zip(psych_questions, numeric_answers), 1):
            output += f"\n{i}. {q.text}\n   {q.options[ans-1]}\n"
        
        return output
        
    except Exception as e:
        return f"Error: {str(e)}"


def process_neuroscience_answers(*answers):
    """Process neuroscience answers and calculate result"""
    try:
        letter_answers = []
        for i, answer in enumerate(answers):
            if answer:
                letter = answer.split(":")[0].strip()
                letter_answers.append(letter)
            else:
                return "Please answer all questions"
        
        if len(letter_answers) != 9:
            return "Please answer all 9 questions"
        
        result = NeuroscienceService.calculate_assessment(letter_answers)
        
        strong_secondary_text = "Yes" if result.strong_secondary else "No"
        
        output = f"""
## Neuroscience Assessment Result

### Score Distribution:

| Pattern | Score |
|---------|-------|
| Fight (A) | {result.scores.A} |
| Flight (B) | {result.scores.B} |
| Freeze (C) | {result.scores.C} |
| Fawn (D) | {result.scores.D} |

---

### Result:

**Dominant Pattern:** {result.dominant}

**Secondary Pattern:** {result.secondary}

**Strong Secondary:** {strong_secondary_text}

---

### Description:

{result.description}

---

**Your answers:**
"""
        for i, (q, ans) in enumerate(zip(neuro_questions, letter_answers), 1):
            ans_text = q.options_text.get(ans, "")
            output += f"\n{i}. {q.text}\n   {ans}: {ans_text}\n"
        
        return output
        
    except Exception as e:
        return f"Error: {str(e)}"


with gr.Blocks(title="Mental Health Assessment", theme=gr.themes.Soft()) as demo:
    
    gr.Markdown(
        """
        # Mental Health Assessment Platform
        
        Select the appropriate assessment from the tabs below
        
        ---
        """
    )
    
    with gr.Tabs():
        with gr.TabItem("Psychology Assessment"):
            gr.Markdown(
                f"""
                ## {psych_questionnaire.title}
                
                ### {psych_questionnaire.description}
                
                ---
                """
            )
            
            psych_answer_components = []
            
            for q in psych_questions:
                with gr.Group():
                    gr.Markdown(f"### Question {q.id}: {q.text}")
                    radio = gr.Radio(
                        choices=q.options,
                        label="Select your answer",
                        interactive=True
                    )
                    psych_answer_components.append(radio)
            
            psych_submit_btn = gr.Button("Submit Answers", variant="primary", size="lg")
            
            gr.Markdown("---")
            psych_output = gr.Markdown(label="Result")
            
            psych_submit_btn.click(
                fn=process_psychology_answers,
                inputs=psych_answer_components,
                outputs=psych_output
            )
        
        with gr.TabItem("Neuroscience Assessment"):
            gr.Markdown(
                f"""
                ## {neuro_questionnaire.title}
                
                ### {neuro_questionnaire.description}
                
                ---
                """
            )
            
            neuro_answer_components = []
            
            for q in neuro_questions:
                with gr.Group():
                    gr.Markdown(f"### Question {q.id}: {q.text}")
                    choices = [f"{opt}: {q.options_text[opt]}" for opt in q.options]
                    radio = gr.Radio(
                        choices=choices,
                        label="Select your answer",
                        interactive=True
                    )
                    neuro_answer_components.append(radio)
            
            neuro_submit_btn = gr.Button("Submit Answers", variant="primary", size="lg")
            
            gr.Markdown("---")
            neuro_output = gr.Markdown(label="Result")
            
            neuro_submit_btn.click(
                fn=process_neuroscience_answers,
                inputs=neuro_answer_components,
                outputs=neuro_output
            )
    
    gr.Markdown(
        """
        ---
        
        ### Notes:
        
        - All questions are required
        - Select the answer closest to your current state
        - Results are for guidance only, not medical diagnosis
        
        **Built with FastAPI + Gradio**
        """
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=8000,
        share=False
    )
