"""
Progress Tracker — Tracks study progress, quiz scores, weak topics, and milestones.
All data stored locally in JSON files per session.
"""

import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

WEAK_TOPIC_THRESHOLD = 0.6  # Score below 60% flags topic as weak


class ProgressTracker:
    def __init__(self, progress: dict, profile: dict = None):
        self.progress = progress or {}
        self.profile = profile or {}

        # Ensure structure
        defaults = {
            "subjects": {},
            "completed_topics": [],
            "quiz_scores": [],
            "weak_topics": [],
            "study_plan": None,
            "milestones": [],
        }
        for key, default in defaults.items():
            if key not in self.progress:
                self.progress[key] = default

    def mark_topic_complete(self, subject: str, topic: str) -> None:
        if not subject or not topic:
            return
        entry = f"{subject}: {topic}"
        if entry not in self.progress["completed_topics"]:
            self.progress["completed_topics"].append(entry)
            logger.info("Topic completed: %s", entry)

        # Update subject-level tracking
        if subject not in self.progress["subjects"]:
            self.progress["subjects"][subject] = {
                "topics_completed": 0,
                "topics_total": 0,
                "quiz_scores": [],
                "status": "in_progress",
            }
        self.progress["subjects"][subject]["topics_completed"] = (
            self.progress["subjects"][subject].get("topics_completed", 0) + 1
        )
        self.progress["subjects"][subject]["status"] = "in_progress"

        # Remove from weak topics if marked complete
        if entry in self.progress["weak_topics"]:
            self.progress["weak_topics"].remove(entry)

    def record_quiz_score(self, subject: str, topic: str, score: int, total: int) -> None:
        if total <= 0:
            return

        percentage = (score / total) * 100
        entry = {
            "subject": subject,
            "topic": topic,
            "score": score,
            "total": total,
            "percentage": round(percentage, 1),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.progress["quiz_scores"].append(entry)
        # Keep last 100 quiz records
        self.progress["quiz_scores"] = self.progress["quiz_scores"][-100:]

        # Update subject quiz scores
        if subject not in self.progress["subjects"]:
            self.progress["subjects"][subject] = {
                "topics_completed": 0,
                "topics_total": 0,
                "quiz_scores": [],
                "status": "in_progress",
            }
        self.progress["subjects"][subject]["quiz_scores"].append({
            "topic": topic,
            "percentage": round(percentage, 1),
            "timestamp": entry["timestamp"],
        })
        # Keep last 20 per subject
        self.progress["subjects"][subject]["quiz_scores"] = (
            self.progress["subjects"][subject]["quiz_scores"][-20:]
        )

        # Flag weak topics
        topic_key = f"{subject}: {topic}"
        if percentage < WEAK_TOPIC_THRESHOLD * 100:
            if topic_key not in self.progress["weak_topics"]:
                self.progress["weak_topics"].append(topic_key)
                logger.info("Weak topic identified: %s (%.1f%%)", topic_key, percentage)
        else:
            # Remove from weak if now passing
            if topic_key in self.progress["weak_topics"]:
                self.progress["weak_topics"].remove(topic_key)

    def add_milestone(self, milestone: str) -> None:
        if not milestone:
            return
        entry = {
            "text": milestone[:200],
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.progress["milestones"].append(entry)
        self.progress["milestones"] = self.progress["milestones"][-50:]

    def get_dashboard(self) -> dict:
        """Build a progress dashboard summary."""
        subjects_info = {}
        for subj, data in self.progress.get("subjects", {}).items():
            quiz_scores = data.get("quiz_scores", [])
            avg_score = (
                sum(q["percentage"] for q in quiz_scores) / len(quiz_scores)
                if quiz_scores else None
            )
            subjects_info[subj] = {
                "topics_completed": data.get("topics_completed", 0),
                "topics_total": data.get("topics_total", 0),
                "avg_quiz_score": round(avg_score, 1) if avg_score is not None else None,
                "status": data.get("status", "not_started"),
                "recent_scores": quiz_scores[-5:],
            }

        all_quizzes = self.progress.get("quiz_scores", [])
        overall_avg = (
            sum(q["percentage"] for q in all_quizzes) / len(all_quizzes)
            if all_quizzes else None
        )

        completed_topics = self.progress.get("completed_topics", [])
        weak_topics = self.progress.get("weak_topics", [])

        # Exam countdown
        exam_date_str = self.profile.get("exam_date", "")
        days_remaining = None
        if exam_date_str:
            try:
                exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
                days_remaining = (exam_date - date.today()).days
            except Exception:
                pass

        # Recommended next topics
        next_recommendations = self._get_next_recommendations()

        return {
            "overall_progress": {
                "completed_topics_count": len(completed_topics),
                "weak_topics_count": len(weak_topics),
                "total_quizzes": len(all_quizzes),
                "overall_avg_score": round(overall_avg, 1) if overall_avg is not None else None,
                "days_to_exam": days_remaining,
            },
            "subjects": subjects_info,
            "completed_topics": completed_topics[-20:],
            "weak_topics": weak_topics[:15],
            "recent_quizzes": all_quizzes[-10:],
            "milestones": self.progress.get("milestones", [])[-10:],
            "recommendations": next_recommendations,
            "has_study_plan": bool(self.progress.get("study_plan")),
            "study_plan_generated_at": (
                self.progress["study_plan"].get("generated_at")
                if self.progress.get("study_plan") else None
            ),
        }

    def _get_next_recommendations(self) -> list:
        """Generate simple next-step recommendations based on progress data."""
        recommendations = []
        weak = self.progress.get("weak_topics", [])
        if weak:
            recommendations.append({
                "type": "weak_topic",
                "message": f"Revise: {weak[0]}",
                "priority": "high",
            })
            if len(weak) > 1:
                recommendations.append({
                    "type": "weak_topic",
                    "message": f"Also revise: {weak[1]}",
                    "priority": "high",
                })

        all_quizzes = self.progress.get("quiz_scores", [])
        if not all_quizzes:
            recommendations.append({
                "type": "quiz",
                "message": "Take a practice quiz to assess your current knowledge",
                "priority": "medium",
            })

        if not self.progress.get("study_plan"):
            recommendations.append({
                "type": "plan",
                "message": "Generate a personalised study plan to organise your revision",
                "priority": "medium",
            })

        return recommendations[:5]
