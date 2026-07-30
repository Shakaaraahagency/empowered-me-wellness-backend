from app import create_app
from extensions import db
from models.testimonial import Testimonial

testimonials = [
    {
        "author_name": "Tola A.",
        "role": "Remote Worker",
        "content": "It's the first habit tracker that didn't make me feel guilty for missing a day. The focus on consistency over perfection is exactly what I needed.",
        "is_approved": True,
        "is_featured": True
    },
    {
        "author_name": "Grace N.",
        "role": "New Parent",
        "content": "The daily check-ins take two minutes and somehow keep me honest with myself. It's a small window of peace in my chaotic mornings.",
        "is_approved": True,
        "is_featured": True
    },
    {
        "author_name": "Marcus T.",
        "role": "Software Engineer",
        "content": "I used to suffer from severe burnout. The guided routines helped me establish clear boundaries between work and personal life.",
        "is_approved": True,
        "is_featured": True
    },
    {
        "author_name": "Elena R.",
        "role": "Wellness Coach Client",
        "content": "Latoya's coaching approach is deeply empathetic. Her manuals don't just tell you what to do; they help you uncover why you want to do it.",
        "is_approved": True,
        "is_featured": False
    },
    {
        "author_name": "David K.",
        "role": "Entrepreneur",
        "content": "Managing stress seemed impossible until I found EmpoweredMe Wellness. The mindfulness techniques are practical and actually fit into a busy schedule.",
        "is_approved": True,
        "is_featured": False
    },
    {
        "author_name": "Sarah J.",
        "role": "Student",
        "content": "The Kemetic Yoga sessions have completely shifted my relationship with my body. I feel stronger, more grounded, and far less anxious about exams.",
        "is_approved": True,
        "is_featured": False
    },
    {
        "author_name": "Michael B.",
        "role": "Creative Director",
        "content": "I was skeptical about mindfulness, but the realistic, grounded approach here won me over. It's not about emptying your mind, it's about focusing your energy.",
        "is_approved": True,
        "is_featured": False
    },
    {
        "author_name": "Priya S.",
        "role": "Healthcare Worker",
        "content": "Working long shifts left me drained. The short 5-minute breathing exercises are my lifeline during breaks. Highly recommend the coaching.",
        "is_approved": True,
        "is_featured": False
    },
    {
        "author_name": "James L.",
        "role": "Busy Parent",
        "content": "The Kid's Yoga program is fantastic! It's the only activity that gets my children to calm down and focus before bedtime.",
        "is_approved": True,
        "is_featured": False
    },
    {
        "author_name": "Anita M.",
        "role": "Freelancer",
        "content": "Tracking my mood patterns helped me realize when I need to step back. The platform feels like a gentle guide rather than a strict taskmaster.",
        "is_approved": True,
        "is_featured": False
    },
    {
        "author_name": "Chris W.",
        "role": "Fitness Enthusiast",
        "content": "I've tried many wellness apps, but the depth of the Mindfulness Manual is unmatched. It feels personalized, rooted in real wisdom.",
        "is_approved": True,
        "is_featured": False
    },
    {
        "author_name": "Olivia H.",
        "role": "Teacher",
        "content": "Self-care always fell to the bottom of my list. EmpoweredMe gave me the tools to prioritize myself without feeling selfish.",
        "is_approved": True,
        "is_featured": False
    }
]

app = create_app()

with app.app_context():
    Testimonial.query.delete()
    for t_data in testimonials:
        db.session.add(Testimonial(**t_data))
    db.session.commit()
    print(f"Successfully seeded {len(testimonials)} testimonials.")
