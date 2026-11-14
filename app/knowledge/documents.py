"""Policy knowledge base documents.

Each key is the source filename, so answers can cite where they came from.
In production you would load policy wordings, regulator bulletins and FAQs
from files or a document store instead.
"""

KNOWLEDGE_BASE = {
    "canada_auto_insurance_guidelines.md": """# Canadian Auto Insurance Guidelines

## Who Regulates Auto Insurance
Auto insurance in Canada is regulated by each province and territory, so rules
and minimum coverage differ across the country. British Columbia (ICBC),
Saskatchewan (SGI) and Manitoba (MPI) have public auto insurers. In Quebec, the
public SAAQ covers bodily injury and private insurers cover vehicle damage. In
the other provinces, private insurers sell auto insurance under rules set by
the provincial regulator.

## Mandatory Coverage
Every province requires drivers to carry:
- Third-party liability: minimum $200,000 in most provinces ($50,000 for
  property damage in Quebec). Many drivers choose $1 million or $2 million.
- Accident benefits: no-fault medical, rehabilitation and income-replacement
  benefits. Amounts vary by province.
- Uninsured automobile coverage: protects you if you're hit by an uninsured
  or unidentified driver (required in most provinces).

## Driving Without Insurance
Driving without valid insurance is illegal in every province. Penalties
include heavy fines (often thousands of dollars), licence suspension and
vehicle impoundment.

## Actual Cash Value (ACV)
ACV is what your vehicle was worth immediately before the loss, based on its
market value, age, kilometres and condition. If your car is stolen or written
off, the insurer pays the ACV minus your deductible, unless you have a Waiver
of Depreciation endorsement.

## Driving Record and Claims-Free Discount
Insurers reward years without at-fault claims with a claims-free discount.
At-fault claims and traffic convictions stay on your record for several years
(commonly 6) and can raise your premium. Your driving record belongs to you,
not your car or your insurer.

## Fault Determination
In provinces with private insurers, fault is assigned using regulated fault
determination rules based on how the collision happened. Your share of fault
decides whether the claim counts against your driving record.

## Reporting a Collision
Report a collision to police if anyone is injured or if damage exceeds your
province's reporting threshold (commonly $1,000–$2,000). Notify your insurer
as soon as possible — most policies require prompt notice of any claim.

## CrownAuto Claim Service Standards
- Claim acknowledged within 2 business days
- Appraiser assigned within 24–72 hours for repairs over $5,000
- Payment within 30 days of an agreed settlement
""",

    "policy_terms.md": """# CrownAuto Auto Policy Terms

## Mandatory Coverages (included in every plan)
- Third-party liability
- Accident benefits
- Uninsured automobile coverage

## Optional Coverage for Your Own Vehicle
- Collision: damage from hitting another vehicle or object, or rolling over
- Comprehensive: theft, vandalism, fire, flood, hail, windstorm, falling
  objects, glass damage and collisions with animals (such as deer)
- All Perils: Collision and Comprehensive combined
- Specified Perils: only the perils named in the policy

## What is NOT Covered
- Normal wear and tear, rust, mechanical or electrical breakdown
- Driving without a valid licence
- Driving while impaired by alcohol or drugs
- Racing or speed contests
- Using your car for ride-sharing or paid delivery without the right
  endorsement or coverage
- Intentional damage
- Driving outside Canada and the United States

## Endorsements (Optional Add-ons)
- Waiver of Depreciation: if a newer car is written off or stolen, pays the
  original purchase price instead of ACV (vehicles up to 2 years old)
- Loss of Use / Rental Car: pays for a rental while your car is repaired
- Accident Forgiveness: your first at-fault claim won't raise your premium
- Family Protection: extra protection if you're injured by an underinsured
  driver
- Roadside Assistance: towing, battery boost, fuel delivery, lockout help
""",

    "faqs.md": """# Frequently Asked Questions

## Q: Can I keep my claims-free discount if I switch insurers?
Yes. Your claims-free discount is based on your driving record, which follows
you. Your new insurer will check your claims history. Ask your current insurer
for a letter of experience confirming your years insured and any claims.

## Q: My policy lapsed. Can I renew?
Driving without insurance is illegal, so stop driving the car until you're
insured. Contact us right away. CrownAuto can usually reinstate a policy that
lapsed less than 30 days ago. A longer gap can raise your premium.

## Q: What is Waiver of Depreciation?
An endorsement for newer vehicles. If your car is written off or stolen, we pay
the original purchase price instead of the depreciated Actual Cash Value. It's
offered on vehicles up to 2 years old for about $90 a year.

## Q: Will a small claim raise my premium?
An at-fault claim can raise your premium and reset your claims-free discount
for several years. Not-at-fault claims usually don't. For small damage, paying
out of pocket can cost less in the long run. Accident Forgiveness protects
your rate after a first at-fault claim.

## Q: What is a deductible?
The amount you pay toward each collision or comprehensive claim before
insurance pays the rest. Common choices are $500 and $1,000. A higher
deductible lowers your premium.

## Q: Is flood damage covered?
Yes, if you have Comprehensive or All Perils coverage. Collision coverage alone
doesn't cover flood, hail or theft.
""",
}
