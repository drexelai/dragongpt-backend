import json
from langchain_openai import ChatOpenAI
from utils import db, prompt, tool_example_to_messages, Data, TMS, SubjectCoursePair
import os
import ast
from model import llm



def generate_example_messages():
    examples = [
        (
            "I'm a freshman and would like to take CS 171, CI 102, CS 164, and ENGL 103 next term. I don't like classes on Fridays and prefer to take my classes later in the day",
            TMS(
                subject_course_pairs=[
                    SubjectCoursePair(subject="CS", course=171),
                    SubjectCoursePair(subject="CI", course=102),
                    SubjectCoursePair(subject="CS", course=164),
                    SubjectCoursePair(subject="ENGL", course=103),
                ],
                excluded_days=["F"],
                start_time_limit=12
            ),
        ),
    ]
    messages = []
    for text, tool_call in examples:
        messages.extend(
            tool_example_to_messages({"input": text, "tool_calls": [tool_call]})
        )
    return messages




def get_llm_output():

    user_input = input("Enter your course scheduling query: ")
    messages=generate_example_messages()
    
    runnable = prompt | llm.with_structured_output(
        schema=Data,
        method='function_calling',
        include_raw=False,
    )
    response = runnable.invoke(
        {
            "text": user_input,
            "examples": messages,
        }
    )
    return response




def generate_query():
    response=get_llm_output()
    subject_course_pairs = [
        (pair.subject, pair.course) for tms in response.people for pair in tms.subject_course_pairs
    ]
    excluded_days = [day for tms in response.people for day in tms.excluded_days]
    start_time_limit = 12

    course_filters = " OR ".join(
        [f"(SubjectCode = '{subject}' AND \"CourseNo\\.\" = {course})" for subject, course in subject_course_pairs]
    )

    day_exclusion_filter = " AND ".join([f"Days_Time NOT LIKE '%{day}%'" for day in excluded_days])
    time_filter = f"CAST(SUBSTR(\"Days_Time1\", 1, INSTR(\"Days_Time1\", ':') - 1) AS INTEGER) >= {start_time_limit}"

    query_parts = [f"({course_filters})"]
    if day_exclusion_filter:
        query_parts.append(day_exclusion_filter)
    if time_filter:
        query_parts.append(time_filter)

    query = f"""
        SELECT *
        FROM winterTms
        WHERE 
            {' AND '.join(query_parts)}
    """
    return query





def get_data_from_tms_db():
    query=generate_query()
    output_response = db.run(query)
    try:
        output_response = ast.literal_eval(output_response)
    except Exception as e:
        print(f"Error parsing output_response: {e}")
        output_response = []
    
    return output_response


def create_json_request():
    output_response=get_data_from_tms_db()
    processed_data = []
    for item in output_response:
        if isinstance(item, (list, tuple)) and len(item) == 13:
            processed_data.append({
                "subject": item[0],
                "course_number": item[1],
                "instruction_type": item[2],
                "delivery_method": item[3],
                "section": item[4],
                "course_url": item[5],
                "crn": item[6],
                "course_title": item[7],
                "day": item[8],
                "time": item[9],
                "start_date": item[10],
                "final_exam": item[11],
                "instructor": item[12]
            })

    with open("data_collection/generated-courses.json", "w") as json_file:
        json.dump(processed_data, json_file, indent=4)

    return processed_data


def main():
    create_json_request()

if __name__ == "__main__":
    main()
