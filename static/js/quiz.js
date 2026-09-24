/**
 * MAT-VLAB — Quiz & Knowledge Assessment Controller
 */

let selectedAnswers = {};
let quizQuestions = [];

function initQuiz(questions) {
  quizQuestions = questions || [];
  selectedAnswers = {};
  renderQuestions();
}

function selectOption(questionId, optionLetter) {
  selectedAnswers[questionId] = optionLetter;

  // Update UI selection
  const card = document.getElementById(`quiz-card-${questionId}`);
  if (!card) return;

  card.querySelectorAll('.quiz-option-btn').forEach(btn => {
    btn.classList.remove('selected-option');
  });

  const selectedBtn = document.getElementById(`opt-${questionId}-${optionLetter}`);
  if (selectedBtn) {
    selectedBtn.classList.add('selected-option');
  }

  // Update answered count
  const answeredCount = Object.keys(selectedAnswers).length;
  const progressBadge = document.getElementById('quiz-answered-count');
  if (progressBadge) {
    progressBadge.textContent = `${answeredCount} of ${quizQuestions.length} answered`;
  }
}

function submitQuiz() {
  if (quizQuestions.length === 0) return;

  const total = quizQuestions.length;
  const answered = Object.keys(selectedAnswers).length;

  if (answered < total) {
    if (!confirm(`You have only answered ${answered} of ${total} questions. Submit anyway?`)) {
      return;
    }
  }

  let score = 0;

  quizQuestions.forEach(q => {
    const userChoice = selectedAnswers[q.id];
    const isCorrect = userChoice === q.correct_option;
    if (isCorrect) score++;

    const card = document.getElementById(`quiz-card-${q.id}`);
    if (!card) return;

    // Reveal correct/incorrect indicators
    card.querySelectorAll('.quiz-option-btn').forEach(btn => {
      const optVal = btn.getAttribute('data-option');
      btn.disabled = true;

      if (optVal === q.correct_option) {
        btn.classList.add('btn-success', 'text-white');
        btn.innerHTML += ' <i class="fas fa-check-circle ms-2"></i> (Correct)';
      } else if (optVal === userChoice && !isCorrect) {
        btn.classList.add('btn-danger', 'text-white');
        btn.innerHTML += ' <i class="fas fa-times-circle ms-2"></i> (Your Choice)';
      }
    });

    // Show scientific explanation
    const expDiv = document.getElementById(`explanation-${q.id}`);
    if (expDiv) {
      expDiv.classList.remove('d-none');
    }
  });

  const percentage = Math.round((score / total) * 100);

  // Show score modal or banner
  const resultBanner = document.getElementById('quiz-result-banner');
  const scoreText = document.getElementById('quiz-score-display');
  const pctText = document.getElementById('quiz-percentage-display');
  const feedbackMsg = document.getElementById('quiz-feedback-message');

  if (resultBanner) resultBanner.classList.remove('d-none');
  if (scoreText) scoreText.textContent = `${score} / ${total}`;
  if (pctText) pctText.textContent = `${percentage}%`;

  if (feedbackMsg) {
    if (percentage >= 80) {
      feedbackMsg.innerHTML = '<span class="text-success fw-bold"><i class="fas fa-award"></i> Outstanding!</span> You demonstrated comprehensive mastery of tensile testing mechanics and ASTM standards.';
    } else if (percentage >= 60) {
      feedbackMsg.innerHTML = '<span class="text-warning fw-bold"><i class="fas fa-thumbs-up"></i> Good Effort!</span> Sound conceptual understanding; review the explanations for missed questions.';
    } else {
      feedbackMsg.innerHTML = '<span class="text-danger fw-bold"><i class="fas fa-book-reader"></i> Needs Revision:</span> Revisit the Tensile Theory and Apparatus sections to reinforce core principles.';
    }
  }

  // Scroll to banner
  if (resultBanner) {
    resultBanner.scrollIntoView({ behavior: 'smooth' });
  }

  // Save score to backend
  fetch('/api/quiz/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      experiment_type: 'tensile',
      score: score,
      total_questions: total
    })
  }).catch(err => console.error("Quiz result save error", err));
}

function resetQuiz() {
  selectedAnswers = {};
  quizQuestions.forEach(q => {
    const card = document.getElementById(`quiz-card-${q.id}`);
    if (!card) return;

    card.querySelectorAll('.quiz-option-btn').forEach(btn => {
      btn.disabled = false;
      btn.className = 'btn form-lab-control w-100 text-start mb-2 quiz-option-btn';
      const optVal = btn.getAttribute('data-option');
      btn.innerHTML = `<strong>${optVal}.</strong> ${q['option_' + optVal.toLowerCase()]}`;
    });

    const expDiv = document.getElementById(`explanation-${q.id}`);
    if (expDiv) expDiv.classList.add('d-none');
  });

  const resultBanner = document.getElementById('quiz-result-banner');
  if (resultBanner) resultBanner.classList.add('d-none');

  const progressBadge = document.getElementById('quiz-answered-count');
  if (progressBadge) progressBadge.textContent = `0 of ${quizQuestions.length} answered`;

  window.scrollTo({ top: 0, behavior: 'smooth' });
}
