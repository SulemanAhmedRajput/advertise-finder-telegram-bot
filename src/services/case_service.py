from typing import Optional
from beanie import PydanticObjectId
from models.case_model import Case, CaseStatus

async def find_case_by_user_id(user_id: int) -> Optional[Case]:
    """
    Find a case by user ID.
    
    :param user_id: The user ID to search for.
    :return: The case if found, otherwise None.
    """
    return await Case.find_one(Case.user_id == user_id)

async def add_or_update_case(case_data: dict) -> Case:
    """
    Add a new case or update an existing case based on the user ID.
    
    :param case_data: The data for the case.
    :return: The added or updated case.
    """
    user_id = case_data.get("user_id")
    existing_case = await find_case_by_user_id(user_id)
    
    if existing_case:
        # Update the existing case
        for key, value in case_data.items():
            setattr(existing_case, key, value)
        await existing_case.save()
        return existing_case
    else:
        # Create a new case
        new_case = Case(**case_data)
        await new_case.insert()
        return new_case
    
    
    
 
async def get_case_by_user(user_id: int) -> Optional[Case]:
    """
    Retrieve a case by user_id. If not found, return None.
    
    Args:
    - user_id (int): The user ID to search for.
    
    Returns:
    - case (Optional[Case]): The found case or None if not found.
    """
    return await Case.find_one({"user_id": user_id})
    
async def update_or_create_case(
    user_id: int,
    **kwargs
) -> Case:
    """
    Update an existing case or create a new one if it doesn't exist.
    
    Args:
    - user_id (int): The user ID for the case to update or create.
    - kwargs (dict): The fields that will be updated or created if not already present.
    
    Returns:
    - case (Case): The updated or newly created case.
    """
    # Try to find an existing case
    case = await get_case_by_user(user_id)
    
    if not case:
        # If no case exists, create a new one
        case = Case(user_id=user_id, status=CaseStatus.DRAFT)
    
    # Update fields if provided
    for key, value in kwargs.items():
        if value is not None:
            setattr(case, key, value)
    
    # Save the case (update or create)
    await case.save()
    return case