import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlmodel import Session


def flush_with_error_handling(
    session: Session,
    *,
    logger: logging.Logger,
    action: str,
    conflict_detail: str = "資料衝突，請重試。",
    failure_detail: str = "資料處理失敗，請稍後再試。",
) -> None:
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        logger.warning("%s: integrity conflict on flush: reason=%s", action, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=conflict_detail,
        ) from exc
    except OperationalError as exc:
        # 🚀 Distinguish connection / operational errors for better observability
        session.rollback()
        logger.error(
            "%s: operational/connection error on flush: reason=%s",
            action,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="資料庫暫時無法連線，請稍後再試。",
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("%s: database error on flush: reason=%s", action, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=failure_detail,
        ) from exc


def commit_with_error_handling(
    session: Session,
    *,
    logger: logging.Logger,
    action: str,
    conflict_detail: str = "資料衝突，請重試。",
    failure_detail: str = "資料寫入失敗，請稍後再試。",
) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        logger.warning("%s: integrity conflict on commit: reason=%s", action, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=conflict_detail,
        ) from exc
    except OperationalError as exc:
        # 🚀 Distinguish connection / operational errors for better observability
        session.rollback()
        logger.error(
            "%s: operational/connection error on commit: reason=%s",
            action,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="資料庫暫時無法連線，請稍後再試。",
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("%s: database error on commit: reason=%s", action, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=failure_detail,
        ) from exc
