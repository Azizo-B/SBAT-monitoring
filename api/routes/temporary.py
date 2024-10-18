from fastapi import APIRouter, Depends

from ..dependencies import get_settings
from ..models.common import ContactFormSubmission
from ..models.settings import Settings
from ..utils import send_telegram_message

router = APIRouter()


@router.post("/contact")
async def contact(contact_form: ContactFormSubmission, settings: Settings = Depends(get_settings)) -> dict[str, str]:
    await send_telegram_message(
        f"{contact_form.name}\n\n{contact_form.email}\n\n{contact_form.subject}\n\n{contact_form.message}",
        settings.telegram_bot_token,
        "7034145945",
    )
    return {"status": "ok"}
