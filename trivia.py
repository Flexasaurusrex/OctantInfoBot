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
                "explanation": "Octant uses Quadratic Funding, which empowers communities by giving greater weight to many small donations over fewer large ones."
            },
            {
                "question": "What is the maximum funding cap for projects in Octant?",
                "options": {
                    "A": "10%",
                    "B": "15%",
                    "C": "20%",
                    "D": "25%"
                },
                "correct": "C",
                "explanation": "Projects have a maximum funding cap of 20% of the Matched Rewards pool to ensure fair distribution."
            },
            {
                "question": "What score is required on Gitcoin Passport for maximum matching funding?",
                "options": {
                    "A": "10",
                    "B": "15",
                    "C": "20",
                    "D": "25"
                },
                "correct": "B",
                "explanation": "Users need a Gitcoin Passport score of 15 or higher to receive maximum available matching funding."
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
                "explanation": "Each Octant epoch lasts 90 days, during which funds are distributed and decisions are made."
            },
            {
                "question": "What happens to donations that don't meet the minimum threshold?",
                "options": {
                    "A": "Returned to donors",
                    "B": "Rolled over to next epoch",
                    "C": "Transferred to Golem Foundation",
                    "D": "Added to matching pool"
                },
                "correct": "C",
                "explanation": "Donations that don't meet the threshold are transferred to the Golem Foundation."
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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❓ Question {len(self.asked_questions)}/{self.total_questions}:

{question['question']}

🔤 Options:
A) {question['options']['A']}
B) {question['options']['B']}
C) {question['options']['C']}
D) {question['options']['D']}

Type A, B, C, or D to answer!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return formatted_question
        
    def check_answer(self, user_answer):
        """Check if the answer is correct and return appropriate response."""
        if not self.asked_questions:
            return "Please start a new game first!"
            
        current_question = self.questions[list(self.asked_questions)[-1]]
        user_answer = user_answer.strip().upper()
        
        if user_answer not in ['A', 'B', 'C', 'D']:
            return "Please answer with A, B, C, or D!"
            
        correct_answer = current_question['correct']
        correct_option = current_question['options'][correct_answer]
        explanation = current_question['explanation']
        
        if user_answer == correct_answer:
            self.score += 1
            response = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Correct! Well done!

📖 {explanation}

📊 Current Score: {self.score}/{self.total_questions}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            response = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Not quite! Let's learn from this one!

🎯 The correct answer was: [{correct_answer}] {correct_option}

📖 Explanation:
{explanation}

📊 Current Score: {self.score}/{self.total_questions}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        if len(self.asked_questions) == self.total_questions:
            response += self.end_game()
        else:
            response += "\n" + self.get_next_question()
            
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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎮 Welcome to Octant Trivia! 🎮
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test your knowledge about Octant's ecosystem, funding mechanisms, 
and community initiatives!

📋 Game Rules:
• Answer each question using A, B, C, or D
• Type 'end trivia' at any time to finish
• Each correct answer earns you points
• Learn interesting facts about Octant!

Get ready for some exciting questions...

""" + self.get_next_question()
