from fastapi import HTTPException, status
from openai import OpenAI, OpenAIError

from app.core.config import settings
from app.schemas.demo import DemoProduct, DemoProductList


def get_openai_client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API key is not configured on the backend",
        )
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_demo_products(count: int = 10) -> list[DemoProduct]:
    client = get_openai_client()
    prompt = (
        f"Generate exactly {count} realistic e-commerce electronics products. "
        f"For each provide a unique SKU, realistic price in INR, and initial inventory quantity (between 5 and 100). "
        f"Return only the requested structured fields. No descriptions."
    )

    try:
        completion = client.beta.chat.completions.parse(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise e-commerce demo data generator producing structured JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format=DemoProductList,
            max_completion_tokens=min(150 * count + 200, 2000),
        )

        parsed_data = completion.choices[0].message.parsed
        if not parsed_data or not parsed_data.products:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenAI returned an empty or invalid product list",
            )
        return parsed_data.products[:count]
    except HTTPException:
        raise
    except OpenAIError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI data generation failed. Please try again.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI data generation failed. Please try again.",
        )
