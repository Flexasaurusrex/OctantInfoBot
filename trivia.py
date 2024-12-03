import random

class Trivia:
    def __init__(self):
        self.questions = [
            {
                "question": "What is Octant's main funding mechanism?",
                "options": {
                    "A": "Traditional Grants",
                    "B": "Quadratic Funding",
                    "C": "Direct Donations",
                    "D": "Private Investment"
                },
                "correct": "B",
                "explanation": "Octant uses Quadratic Funding which considers both the number of unique contributors and the amount donated, giving more weight to projects with broad community support."
            },
            {
                "question": "What percentage of staking yield contributes to Octant's Total Rewards budget?",
                "options": {
                    "A": "50%",
                    "B": "60%",
                    "C": "70%",
                    "D": "80%"
                },
                "correct": "C",
                "explanation": "70% of the staking yield contributes to Octant's Total Rewards budget, split evenly between User Rewards and Matched Rewards."
            },
            {
                "question": "What is the minimum effective GLM balance required to qualify for user rewards?",
                "options": {
                    "A": "1 GLM",
                    "B": "50 GLM",
                    "C": "100 GLM",
                    "D": "500 GLM"
                },
                "correct": "C",
                "explanation": "While you can lock as little as 1 GLM, a minimum effective balance of 100 GLM is required to qualify for user rewards."
            },
            {
                "question": "How long is an Octant epoch?",
                "options": {
                    "A": "30 days",
                    "B": "60 days",
                    "C": "90 days",
                    "D": "120 days"
                },
                "correct": "C",
                "explanation": "Each Octant epoch lasts 90 days, followed by a two-week allocation window where users can claim rewards or donate to projects."
            },
            {
                "question": "What is the maximum funding cap for a single project from the Matched Rewards pool?",
                "options": {
                    "A": "10%",
                    "B": "15%",
                    "C": "20%",
                    "D": "25%"
                },
                "correct": "C",
                "explanation": "A maximum funding cap of 20% of the total Matched Rewards fund (including Patron mode) ensures balanced distribution. Users can still donate to projects at the cap, but these won't receive additional matching."
            }
        ]
        self.score = 0
        self.total_questions = len(self.questions)
        self.asked_questions = set()
        
    def reset_game(self):
        """Reset the game state."""
        self.score = 0
        self.asked_questions = set()
        
    def get_next_question(self):
        """Get the next random question."""
        available_questions = [i for i in range(len(self.questions)) 
                             if i not in self.asked_questions]
        
        if not available_questions:
            return self.end_game()
            
        question_index = random.choice(available_questions)
        self.asked_questions.add(question_index)
        question = self.questions[question_index]
        
        formatted_question = f"""
<div class="trivia-container">
    <div class="trivia-score">Question {len(self.asked_questions)}/{self.total_questions}</div>
    
    <div class="trivia-question">
        {question['question']}
    </div>
    
    <div class="trivia-options">
        <div class="trivia-option" data-option="A">
            <strong>A)</strong> {question['options']['A']}
        </div>
        <div class="trivia-option" data-option="B">
            <strong>B)</strong> {question['options']['B']}
        </div>
        <div class="trivia-option" data-option="C">
            <strong>C)</strong> {question['options']['C']}
        </div>
        <div class="trivia-option" data-option="D">
            <strong>D)</strong> {question['options']['D']}
        </div>
    </div>
    
    <div style="text-align: center; font-size: 0.9rem;">
        Type A, B, C, or D to answer!
    </div>
</div>
"""
        return formatted_question
        
    def check_answer(self, user_answer):
        """Check if the answer is correct and return appropriate response."""
        if not self.asked_questions:
            return "Please start a new game first!"
            
        # Get the last question that was asked
        current_question_index = max(self.asked_questions)
        current_question = self.questions[current_question_index]
        user_answer = user_answer.strip().upper()
        
        if user_answer not in ['A', 'B', 'C', 'D']:
            return "Please answer with A, B, C, or D!"
            
        correct_answer = current_question['correct']
        correct_option = current_question['options'][correct_answer]
        explanation = current_question['explanation']
        
        if user_answer == correct_answer:
            self.score += 1
            response = f"""
<div class="trivia-container">
    <div class="trivia-score" style="color: #28a745">✅ Correct! Well done!</div>
    
    <div class="trivia-explanation">
        {explanation}
    </div>
    
    <div class="trivia-score">
        Current Score: {self.score}/{self.total_questions}
    </div>

    <div class="trivia-actions">
        <button class="trivia-button" onclick="document.getElementById('message-input').value='next question';document.getElementById('send-button').click()">Next Question</button>
        <button class="trivia-button secondary" onclick="document.getElementById('message-input').value='end trivia';document.getElementById('send-button').click()">End Game</button>
    </div>
</div>
"""
            return response
        else:
            response = f"""
<div class="trivia-container">
    <div class="trivia-score" style="color: #dc3545">❌ Not quite! Let's learn from this one!</div>
    
    <div style="margin: 1rem 0;">
        <strong>The correct answer was:</strong><br>
        [{correct_answer}] {correct_option}
    </div>
    
    <div class="trivia-explanation">
        {explanation}
    </div>
    
    <div class="trivia-score">
        Current Score: {self.score}/{self.total_questions}
    </div>

    <div class="trivia-actions">
        <button class="trivia-button" onclick="document.getElementById('message-input').value='next question';document.getElementById('send-button').click()">Next Question</button>
        <button class="trivia-button secondary" onclick="document.getElementById('message-input').value='end trivia';document.getElementById('send-button').click()">End Game</button>
    </div>
</div>
"""
            if len(self.asked_questions) == self.total_questions:
                return response + "\n" + self.end_game()
            return response
        
    def end_game(self):
        """End the game and show final score."""
        percentage = (self.score / self.total_questions) * 100
        response = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎮 Game Over!

🏆 Final Score: {self.score}/{self.total_questions} ({percentage:.1f}%)

Want to play again? Type 'start trivia'!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return response
        
    def start_game(self):
        """Start a new game."""
        self.reset_game()
        return """
<div class="trivia-container">
    <div class="trivia-score" style="font-size: 1.4rem">🎮 Welcome to Octant Trivia! 🎮</div>
    
    <div style="margin: 1.5rem 0; text-align: center;">
        Test your knowledge about Octant's ecosystem, funding mechanisms,
        and community initiatives!
    </div>
    
    <div style="background-color: var(--message-bg); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
        <strong>📋 Game Rules:</strong>
        <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
            <li>Answer each question using A, B, C, or D</li>
            <li>Type 'end trivia' at any time to finish</li>
            <li>Each correct answer earns you points</li>
            <li>Learn interesting facts about Octant!</li>
        </ul>
    </div>
    
    <div style="text-align: center; margin: 1rem 0;">
        Get ready for some exciting questions...
    </div>
</div>
""" + self.get_next_question()
