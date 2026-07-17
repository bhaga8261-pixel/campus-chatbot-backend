import asyncio
import logging
from datetime import datetime, timedelta
from app.database.connection import connect_to_mongo, close_mongo_connection, get_collection
from app.auth.jwt_handler import hash_password
from app.services.embedding import embedding_service
from bson import ObjectId

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def seed_database():
    logger.info("Initializing database seeding...")
    await connect_to_mongo()
    
    users_collection = get_collection("users")
    documents_collection = get_collection("documents")
    chunks_collection = get_collection("document_chunks")
    notices_collection = get_collection("notices")
    events_collection = get_collection("events")
    faq_collection = get_collection("faq")
    chats_collection = get_collection("chats")

    # Clear existing seed data if any (optional, but good for idempotent seeds)
    logger.info("Clearing existing collections...")
    await users_collection.delete_many({})
    await documents_collection.delete_many({})
    await chunks_collection.delete_many({})
    await notices_collection.delete_many({})
    await events_collection.delete_many({})
    await faq_collection.delete_many({})
    await chats_collection.delete_many({})

    # 1. Create Indexes
    logger.info("Creating database indexes...")
    await users_collection.create_index("email", unique=True)
    
    # 2. Seed Users
    logger.info("Seeding users...")
    admin_id = ObjectId()
    student_id = ObjectId()
    
    users = [
        {
            "_id": admin_id,
            "name": "Admin Coordinator",
            "email": "admin@college.edu",
            "password": hash_password("admin123"),
            "role": "admin",
            "created_at": datetime.utcnow()
        },
        {
            "_id": student_id,
            "name": "Rahul Sharma",
            "email": "student@college.edu",
            "password": hash_password("student123"),
            "role": "student",
            "created_at": datetime.utcnow()
        }
    ]
    await users_collection.insert_many(users)
    logger.info("Users seeded successfully: admin@college.edu, student@college.edu")

    # 3. Seed Notices
    logger.info("Seeding notices...")
    notices = [
        {
            "title": "End-Semester Examinations July 2026 Schedule",
            "description": (
                "The end-semester exam schedule for all branches has been released. "
                "Exams will commence on July 20, 2026, and conclude by August 5, 2026. "
                "Students can download the detailed time table from the departmental bulletin boards."
            ),
            "createdAt": datetime.utcnow() - timedelta(days=2)
        },
        {
            "title": "Diwali Vacation Holidays Announcement",
            "description": (
                "The college will remain closed from November 10, 2026, to November 18, 2026, "
                "on account of the Diwali holidays. Normal classes will resume on November 19, 2026."
            ),
            "createdAt": datetime.utcnow() - timedelta(days=5)
        },
        {
            "title": "Odd-Semester College Fee Payment Deadline Extended",
            "description": (
                "The final date for submission of the academic term fee for all B.Tech and MCA courses "
                "has been extended to July 30, 2026 without late fines. Please pay at the bank counter or online portal."
            ),
            "createdAt": datetime.utcnow() - timedelta(days=1)
        }
    ]
    await notices_collection.insert_many(notices)

    # 4. Seed Events
    logger.info("Seeding events...")
    events = [
        {
            "title": "TechFest '26 - Annual Technical Symposium",
            "date": datetime.utcnow() + timedelta(days=10),
            "description": (
                "TechFest is back with exciting events like RoboWar, Hackathon, Coding Competitions, "
                "and paper presentations. Cash prizes worth Rs 2 Lakhs to be won. Registrations close in 5 days."
            )
        },
        {
            "title": "Annual Sports Meet 2026",
            "date": datetime.utcnow() + timedelta(days=25),
            "description": (
                "Join us for the Inter-departmental Athletics, Football, Cricket, and Badminton tournaments. "
                "Register your team with the Physical Education Coordinator before next Friday."
            )
        },
        {
            "title": "Campus Career Placement Drive - Microsoft & TCS",
            "date": datetime.utcnow() + timedelta(days=15),
            "description": (
                "A campus placement drive for final year B.Tech CS, MCA, and ECE students will be held "
                "in the seminar hall. Microsoft will present on Day 1, followed by TCS on Day 2. Please carry 3 copies of resume."
            )
        }
    ]
    await events_collection.insert_many(events)

    # 5. Seed FAQ
    logger.info("Seeding FAQs...")
    faqs = [
        {
            "question": "What are the timings of the Central College Library?",
            "answer": "The central library is open from 9:00 AM to 8:00 PM on working days (Monday-Friday) and from 10:00 AM to 5:00 PM on Saturdays. It remains closed on Sundays."
        },
        {
            "question": "What is the fee structure for hostel accommodation?",
            "answer": "Hostel fee is Rs 45,000 per semester. It includes lodging, electricity, maintenance, and access to common facilities. Mess charge is Rs 3,000 per month charged additionally."
        },
        {
            "question": "How can I apply for a character or transfer certificate?",
            "answer": "You can request a character or transfer certificate by filling out the application form available at the administration window, obtaining clearances from the library, laboratory and finance heads, and submitting it to the Registrar."
        }
    ]
    await faq_collection.insert_many(faqs)

    # 6. Seed Documents and Chunks (for RAG testing)
    logger.info("Seeding sample document and embedding chunks...")
    doc_id = ObjectId()
    doc_title = "Data Structures And Algorithms Syllabus"
    doc_filename = "dsa_syllabus_2026.pdf"
    
    document = {
        "_id": doc_id,
        "title": doc_title,
        "filename": doc_filename,
        "uploadedBy": admin_id,
        "uploadedAt": datetime.utcnow()
    }
    await documents_collection.insert_one(document)

    syllabus_chunks = [
        {
            "text": (
                "Data Structures and Algorithms (DSA) Course Syllabus - Code: CS-301. "
                "Branch: Computer Science & Engineering. Course Credits: 4. "
                "Semester: 3rd. Objective: To study fundamental data structures like Arrays, "
                "Linked Lists, Stacks, Queues, Trees, and Graphs, and analyze algorithm complexities."
            ),
            "page": 1
        },
        {
            "text": (
                "Unit 1: Linear Data Structures. Arrays: Representation, address calculation, operations. "
                "Linked Lists: Singly, doubly, and circular linked lists, insertion and deletion operations. "
                "Stacks and Queues: Array and linked list representation, infix to postfix conversions, recursion."
            ),
            "page": 1
        },
        {
            "text": (
                "Unit 2: Non-Linear Data Structures. Binary Trees: Traversals (Inorder, Preorder, Postorder), "
                "Binary Search Trees (BST) operations (Search, Insertion, Deletion). "
                "Graphs: Matrix and adjacency list representation, BFS and DFS traversals, Spanning Trees."
            ),
            "page": 2
        },
        {
            "text": (
                "Unit 3: Sorting and Searching. Searching: Linear search, binary search. "
                "Sorting: Bubble sort, insertion sort, selection sort, quicksort, merge sort, heap sort. "
                "Time complexities: worst-case, average-case, best-case complexities using Big-O notation."
            ),
            "page": 2
        },
        {
            "text": (
                "College Examinations Reference: Mid-term exam covers Unit 1 and Unit 2. "
                "Final semester exam covers all units. Recommended Books: 'Data Structures' by Lipschutz, "
                "'Introduction to Algorithms' by Cormen, Leiserson, Rivest, and Stein."
            ),
            "page": 3
        }
    ]

    db_chunks = []
    for idx, sc in enumerate(syllabus_chunks):
        text = sc["text"]
        logger.info(f"Generating embedding for chunk {idx+1}/{len(syllabus_chunks)}...")
        embedding = embedding_service.get_embedding(text)
        db_chunks.append({
            "documentId": doc_id,
            "chunk": text,
            "embedding": embedding,
            "page": sc["page"],
            "metadata": {
                "document_name": doc_title,
                "filename": doc_filename,
                "uploaded_at": datetime.utcnow().isoformat(),
                "start_idx": 0,
                "end_idx": len(text)
            }
        })
        
    await chunks_collection.insert_many(db_chunks)
    logger.info("Successfully seeded syllabus document vector chunks.")

    await close_mongo_connection()
    logger.info("Database seeding successfully completed!")

if __name__ == "__main__":
    asyncio.run(seed_database())
