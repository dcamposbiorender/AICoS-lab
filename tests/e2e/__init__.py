"""
End-to-End Tests for AICoS Lab

Lab-grade E2E testing that actually uses the system like real users would.
No mocks, no stubs - just run the damn code and see if it works.

Based on learnings from CRM testing experience:
- Integration bugs are found by running real workflows
- API mismatches surface when components actually talk to each other  
- Data format assumptions break when real data flows through
- Initialization and performance issues only show up under real usage

Test Philosophy:
1. Use real components, not mocks
2. Test actual user workflows
3. Find bugs in seconds, not hours
4. Pragmatic over comprehensive
5. Fix issues immediately when found
"""