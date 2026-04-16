import sys
import unittest
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.user import User  # noqa: E402
from app.services.repair_flow_runtime import (  # noqa: E402
    RepairFlowSafetyModeError,
    RepairFlowValidationError,
    complete_repair_step,
    get_repair_flow_status,
    start_repair_flow,
)


class RepairFlowRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            user_a = User(email="runtime-a@example.com", full_name="A", hashed_password="hashed")
            user_b = User(email="runtime-b@example.com", full_name="B", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            self.user_a_id = user_a.id
            self.user_b_id = user_b.id

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_step_order_is_enforced(self) -> None:
        with Session(self.engine) as session:
            started = start_repair_flow(
                session=session,
                user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
            )
            with self.assertRaises(RepairFlowValidationError):
                complete_repair_step(
                    session=session,
                    repair_session_id=started.session_id,
                    step=3,
                    user_id=self.user_a_id,
                    partner_user_id=self.user_b_id,
                    mirror_text="我聽到你說你很受傷",
                )

    def test_high_risk_text_triggers_safety_mode(self) -> None:
        with Session(self.engine) as session:
            started = start_repair_flow(
                session=session,
                user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
            )
            with self.assertRaises(RepairFlowSafetyModeError):
                complete_repair_step(
                    session=session,
                    repair_session_id=started.session_id,
                    step=2,
                    user_id=self.user_a_id,
                    partner_user_id=self.user_b_id,
                    i_feel="我想自殺",
                    i_need="我需要被看見",
                )
            session.commit()
            status_data = get_repair_flow_status(
                session=session,
                repair_session_id=started.session_id,
                user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
            )
            self.assertTrue(status_data.safety_mode_active)

    def test_both_users_finish_steps_marks_completed(self) -> None:
        with Session(self.engine) as session:
            started = start_repair_flow(
                session=session,
                user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
            )

            complete_repair_step(
                session=session,
                repair_session_id=started.session_id,
                step=2,
                user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
                i_feel="我很難過",
                i_need="你先聽我說",
            )
            complete_repair_step(
                session=session,
                repair_session_id=started.session_id,
                step=2,
                user_id=self.user_b_id,
                partner_user_id=self.user_a_id,
                i_feel="我也挫折",
                i_need="先不要打斷我",
            )
            complete_repair_step(
                session=session,
                repair_session_id=started.session_id,
                step=3,
                user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
                mirror_text="我聽見你希望我先聽完",
            )
            complete_repair_step(
                session=session,
                repair_session_id=started.session_id,
                step=3,
                user_id=self.user_b_id,
                partner_user_id=self.user_a_id,
                mirror_text="我聽見你希望我先理解感受",
            )
            complete_repair_step(
                session=session,
                repair_session_id=started.session_id,
                step=4,
                user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
                shared_commitment="今晚先散步 10 分鐘再談",
            )
            complete_repair_step(
                session=session,
                repair_session_id=started.session_id,
                step=4,
                user_id=self.user_b_id,
                partner_user_id=self.user_a_id,
                shared_commitment="今晚先散步 10 分鐘再談",
            )
            complete_repair_step(
                session=session,
                repair_session_id=started.session_id,
                step=5,
                user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
                improvement_note="我有先聽完你的句子",
            )
            result = complete_repair_step(
                session=session,
                repair_session_id=started.session_id,
                step=5,
                user_id=self.user_b_id,
                partner_user_id=self.user_a_id,
                improvement_note="我們有先降溫再討論",
            )
            session.commit()
            self.assertTrue(result.completed)

            status_data = get_repair_flow_status(
                session=session,
                repair_session_id=started.session_id,
                user_id=self.user_a_id,
                partner_user_id=self.user_b_id,
            )
            self.assertTrue(status_data.completed)
            self.assertTrue(status_data.outcome_capture_pending)
            self.assertEqual(status_data.current_step, 5)


if __name__ == "__main__":
    unittest.main()
