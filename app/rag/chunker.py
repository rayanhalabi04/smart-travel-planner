from typing import Any


def build_destination_documents(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    documents = []

    for index, row in enumerate(rows):
        destination_name = str(row["destination_name"]).strip()
        country = str(row["country"]).strip()
        travel_style = str(row["travel_style"]).strip()

        text = (
            f"{destination_name} is a destination in {country}. "
            f"It is recommended for {travel_style} travel."
        )

        documents.append(
            {
                "id": f"destination-{index}",
                "text": text,
                "metadata": {
                    "destination_name": destination_name,
                    "country": country,
                    "travel_style": travel_style,
                    "source": "cleaned_dataset",
                },
            }
        )

    return documents