import pathlib
file_path = pathlib.Path(r'h:\내 드라이브\sync\군부대 민간위탁 계약상 전시 계속이행 조항에 대한 연구, 불가항력, 부당조건, 사정변경 법리 적용 가능성에 대한 검토.md')

content = file_path.read_text(encoding='utf-8', errors='replace')

c1_part = "과거 농·축·수협과의 수의계약에 의존하던 식재료 조달은 2025년부터 전량 경쟁조달로 전환되어 민간 위탁업체가 직접 식재료를 조달하는 방식으로 변경되었다."
r1_part = "식재료 조달에 있어서는 2021년 '군 급식 개선 종합대책'에서 농·축·수협 수의계약을 단계적으로 축소하여 2025년 전량 경쟁조달로 전환하겠다는 계획이 발표된 바 있으나, 농어업계의 반발과 안정적 공급 필요성 등을 이유로 당초 계획이 수정되어 2025년 '군 급식방침'에서는 농·축·수협과의 수의계약 비중을 2024년과 동일한 70% 수준으로 유지하고 나머지 30%를 경쟁입찰로 운영하는 것으로 최종 결정되었다."

c3_part = "기준을 제시하였다. [^7] 나아가"
r3_part = "기준을 제시하였다. [^2] [^7] 나아가"

if c1_part in content:
    content = content.replace(c1_part, r1_part)
    print("Fixed c1")
else:
    print("Failed c1")

if c3_part in content:
    content = content.replace(c3_part, r3_part)
    print("Fixed c3")
else:
    print("Failed c3")

file_path.write_text(content, encoding='utf-8')
