import random
import html

class Trivia:
    def __init__(self):
        """Initialize the trivia game with questions."""
        self.questions = [
            {
                "question": "What is the minimum effective GLM balance required for user rewards?",
                "options": {
                    "A": "10 GLM",
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
            },
            {
                "question": "What percentage of Octant's rewards goes to foundation operations?",
                "options": {
                    "A": "15%",
                    "B": "20%",
                    "C": "25%",
                    "D": "30%"
                },
                "correct": "C",
                "explanation": "25% of Octant's rewards are allocated to foundation operations to maintain and develop the platform, while 70% goes to user and matched rewards, and 5% to community initiatives."
            },
            {
                "question": "What is the purpose of Patron mode in Octant?",
                "options": {
                    "A": "To increase personal rewards",
                    "B": "To boost project funding",
                    "C": "To skip voting periods",
                    "D": "To reduce fees"
                },
                "correct": "B",
                "explanation": "Patron mode allows users to boost project funding by allocating their rewards directly to the matched rewards pool, enhancing the support for community projects."
            },
            {
                "question": "How much ETH backs Octant's operations?",
                "options": {
                    "A": "50,000 ETH",
                    "B": "75,000 ETH",
                    "C": "100,000 ETH",
                    "D": "125,000 ETH"
                },
                "correct": "C",
                "explanation": "Octant is backed by 100,000 ETH from the Golem Foundation, providing a substantial foundation for its public goods funding initiatives."
            },
            {
                "question": "What happens after each 90-day epoch in Octant?",
                "options": {
                    "A": "Immediate reward distribution",
                    "B": "Two-week allocation window",
                    "C": "One-month voting period",
                    "D": "System maintenance"
                },
                "correct": "B",
                "explanation": "After each 90-day epoch, there's a two-week allocation window where users can claim their rewards or choose to donate them to projects."
            },
            {
                "question": "What percentage of rewards goes to community initiatives?",
                "options": {
                    "A": "5%",
                    "B": "10%",
                    "C": "15%",
                    "D": "20%"
                },
                "correct": "A",
                "explanation": "5% of rewards are allocated to community initiatives, fostering growth and innovation within the Octant ecosystem."
            },
            {
                "question": "What type of staking mechanism does Octant use for GLM tokens?",
                "options": {
                    "A": "Liquid staking",
                    "B": "Locked staking",
                    "C": "Flexible staking",
                    "D": "Delegated staking"
                },
                "correct": "B",
                "explanation": "Octant uses a locked staking mechanism where GLM tokens must be locked to participate in the ecosystem and earn rewards."
            },
            {
                "question": "Which organization oversees Octant's development?",
                "options": {
                    "A": "Ethereum Foundation",
                    "B": "Golem Foundation",
                    "C": "Octant DAO",
                    "D": "Decentralized Council"
                },
                "correct": "B",
                "explanation": "The Golem Foundation oversees Octant's development, backed by their commitment of 100,000 ETH to support public goods funding."
            },
            {
                "question": "What is the primary goal of Octant's funding model?",
                "options": {
                    "A": "Maximum profit generation",
                    "B": "Token price stability",
                    "C": "Public goods funding",
                    "D": "Network security"
                },
                "correct": "C",
                "explanation": "Octant's primary goal is to support public goods funding through its innovative quadratic funding mechanism and community-driven allocation."
            },
            {
                "question": "How are project funding decisions made in Octant?",
                "options": {
                    "A": "Foundation decides alone",
                    "B": "Community voting only",
                    "C": "Quadratic funding + community",
                    "D": "Random selection"
                },
                "correct": "C",
                "explanation": "Project funding in Octant is determined through a combination of quadratic funding mechanics and community participation, ensuring fair and democratic resource allocation."
            },
            {
                "question": "What happens to GLM tokens during the locking period?",
                "options": {
                    "A": "They're burned",
                    "B": "They're traded freely",
                    "C": "They're locked and illiquid",
                    "D": "They're converted to ETH"
                },
                "correct": "C",
                "explanation": "During the locking period, GLM tokens become illiquid and cannot be transferred or traded, ensuring committed participation in the ecosystem."
            }
        ]
        self.score = 0
        self.total_questions = len(self.questions)
        self.asked_questions = set()
        self.current_question = None
        
    def reset_game(self):
        """Reset the game state."""
        self.score = 0
        self.asked_questions = set()
        self.current_question = None
        
    def get_next_question(self):
        """Get the next random question."""
        available_questions = [i for i in range(len(self.questions)) 
                             if i not in self.asked_questions]
        
        if not available_questions:
            return self.end_game()
            
        question_index = random.choice(available_questions)
        self.asked_questions.add(question_index)
        self.current_question = self.questions[question_index]
        
        formatted_question = f"""
<div class="trivia-container">
    <div class="trivia-score">Question {len(self.asked_questions)}/{self.total_questions}</div>
    
    <div class="trivia-question">
        {self.current_question['question']}
    </div>
    
    <div class="trivia-options">
        <div class="trivia-option" data-option="A">
            <strong>A)</strong> {self.current_question['options']['A']}
        </div>
        <div class="trivia-option" data-option="B">
            <strong>B)</strong> {self.current_question['options']['B']}
        </div>
        <div class="trivia-option" data-option="C">
            <strong>C)</strong> {self.current_question['options']['C']}
        </div>
        <div class="trivia-option" data-option="D">
            <strong>D)</strong> {self.current_question['options']['D']}
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
        if not self.current_question:
            return "Please start a new game first!"
            
        user_answer = user_answer.strip().upper()
        
        if user_answer not in ['A', 'B', 'C', 'D']:
            return "Please answer with A, B, C, or D!"
        
        correct_answer = self.current_question['correct']
        correct_option = self.current_question['options'][correct_answer]
        explanation = self.current_question['explanation']
        
        if user_answer == correct_answer:
            self.score += 1
            response = f"""
<div class="trivia-container">
    <div class="trivia-score" style="color: #28a745">✅ Correct! Well done!</div>
    
    <div class="trivia-explanation">
        {explanation}
    </div>
    
    <div class="trivia-score">
        Current Score: {self.score}/{len(self.asked_questions)}
    </div>

    <div class="trivia-actions">
        <button class="trivia-button" onclick="document.getElementById('message-input').value='next question';document.getElementById('send-button').click()">Next Question</button>
        <button class="trivia-button secondary" onclick="document.getElementById('message-input').value='end trivia';document.getElementById('send-button').click()">End Game</button>
    </div>
</div>
"""
        else:
            response = f"""
<div class="trivia-container">
    <div class="trivia-score" style="color: #dc3545">❌ Not quite! Let's learn from this one!</div>
    
    <div style="margin: 1rem 0;">
        <strong>The correct answer was:</strong><br>
        {correct_answer}) {correct_option}
    </div>
    
    <div class="trivia-explanation">
        {explanation}
    </div>
    
    <div class="trivia-score">
        Current Score: {self.score}/{len(self.asked_questions)}
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
        if self.current_question:
            return "You're already in a game! Please finish the current game or type 'end trivia' to start a new one."
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
