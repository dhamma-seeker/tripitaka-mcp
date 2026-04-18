# 🙏 Credits & Acknowledgments

โครงการ **Tripitaka MCP** ไม่อาจเกิดขึ้นได้หากปราศจากความกรุณาและวิริยะของครูบาอาจารย์
ผู้รวบรวม ผู้แปล และชุมชนต่างๆ ที่ได้เมตตาจัดทำข้อมูลพระไตรปิฎกและธรรมะให้ผู้ใฝ่ศึกษาได้เข้าถึง

ขอแสดงความเคารพและอนุโมทนาบุญต่อทุกท่านและทุกแหล่งที่ระบุไว้ด้านล่างนี้

---

## 📚 แหล่งข้อมูลหลัก

### 1. พจนานุกรมพุทธศาสน์ ฉบับประมวลศัพท์

**เรียบเรียงโดย**: สมเด็จพระพุทธโฆษาจารย์ (ป. อ. ปยุตฺโต)
**เผยแผ่โดย**: วัดญาณเวศกวัน
**License**: ธรรมทาน (Dhamma Dāna) — ห้ามใช้เชิงพาณิชย์

- ต้นฉบับทางการ: [watnyanaves.net](https://www.watnyanaves.net)
- ฉบับออนไลน์: [84000.org](https://84000.org)
- ข้อมูลใน repo นี้ scrape จาก: `tripitaka-online.blogspot.com`

โครงการนี้ได้รับประโยชน์จากผลงานของท่านเจ้าประคุณสมเด็จฯ
ด้วยความเคารพอย่างสูงและเพียรรักษาเนื้อหาให้ถูกตรงตามต้นฉบับที่สุด
ตามเจตนารมณ์แห่งธรรมทาน

**สำหรับผู้ต้องการอ้างอิงอย่างเป็นทางการ**: กรุณาใช้หนังสือฉบับพิมพ์ล่าสุด
(ปัจจุบันปี พ.ศ. 2569 พิมพ์ครั้งที่ 35)

### 2. SuttaCentral bilara-data

**ผู้จัดทำ**: ชุมชน SuttaCentral
**License**: [CC0 1.0 Universal (Public Domain Dedication)](https://creativecommons.org/publicdomain/zero/1.0/)

- Repository: [github.com/suttacentral/bilara-data](https://github.com/suttacentral/bilara-data)
- เว็บไซต์: [suttacentral.net](https://suttacentral.net)

ขอขอบคุณชุมชน SuttaCentral สำหรับการจัดทำพระไตรปิฎกดิจิทัล
ที่มีโครงสร้าง segment-level alignment ระหว่างบาลีและคำแปล
ทำให้งาน Dictionary Bridge และ Translation Comparison เป็นไปได้

### 3. คำแปลไทย (CC0)

**ผู้แปล**:
- **พระธีรนันโท (Dhiranandi)** — คำแปลภาษาไทยบางส่วน
- **พระอาจารย์ชยสาโร (Ajahn Jayasaro)** — คำแปลภาษาไทยบางส่วน

**License**: CC0 1.0 (ผ่านโครงการ SuttaCentral)

ขออนุโมทนาต่อพระเถระทั้งสองรูปที่ได้แปลพระสูตรเป็นภาษาไทยที่เข้าใจง่าย
และเปิดให้ใช้ได้อย่างเสรี

### 4. พจนานุกรมภาษาอังกฤษ

#### Pali Text Society Dictionary (PTS)
**เรียบเรียงโดย**: T. W. Rhys Davids & William Stede
**License**: Public Domain
**ที่มา**: [palitextsociety.org](https://www.palitextsociety.org)

#### Dictionary of Pali Proper Names (DPPN)
**เรียบเรียงโดย**: G. P. Malalasekera
**License**: Public Domain
**ที่มา**: [palikanon.com](https://www.palikanon.com/english/pali_names/dic_idx.html)

#### A Buddhist Dictionary
**เรียบเรียงโดย**: Bhikkhu Dhammika
**License**: Creative Commons
**ที่มา**: [bhantedhammika.net](https://www.bhantedhammika.net)

---

## 🛠️ Software & Libraries

โครงการนี้พึ่งพา open source software ต่อไปนี้:

- **[FastMCP](https://github.com/jlowin/fastmcp)** — MCP Server framework
- **[PostgreSQL](https://www.postgresql.org)** — ฐานข้อมูลหลัก
- **[pgvector](https://github.com/pgvector/pgvector)** — Vector similarity search extension
- **[sentence-transformers](https://www.sbert.net)** — Embedding generation
- **[Hugging Face](https://huggingface.co)** — Model hosting & distribution
- **[Docker](https://www.docker.com)** — Containerization
- **[Terraform](https://www.terraform.io)** — Infrastructure as Code

---

## 🌐 Infrastructure

- **[DigitalOcean](https://www.digitalocean.com)** — Cloud hosting สำหรับ public instance
- **[Cloudflare](https://www.cloudflare.com)** — CDN & DDoS protection
- **[GitHub](https://github.com)** — Code hosting
- **[Hugging Face Datasets](https://huggingface.co/datasets)** — Data distribution

---

## 💛 Personal Thanks

ขอขอบคุณครูบาอาจารย์ทุกท่านที่ได้ประสิทธิ์ประสาทความรู้ทางธรรม
ขอบคุณเพื่อนๆ ที่ทดสอบและให้ข้อเสนอแนะในระหว่างการพัฒนา
และขอบคุณผู้มีส่วนร่วมทุกท่านที่จะเข้ามาช่วยพัฒนาโครงการนี้ต่อไป

---

## 🤝 Become a Contributor

หากท่านต้องการร่วมสนับสนุนโครงการนี้:

- **Report bugs / errors**: [GitHub Issues](https://github.com/Ipurak/tripitaka-mcp/issues)
- **Improve translations**: Pull requests ยินดีต้อนรับ
- **Add new dictionaries**: ช่วยเพิ่มแหล่งพจนานุกรมที่ license compatible
- **Translate UI**: ช่วยแปลเอกสารเป็นภาษาอื่น
- **Share**: บอกต่อให้ผู้สนใจธรรมได้รู้จักเครื่องมือนี้

รายละเอียดการร่วมพัฒนา: ดู `CONTRIBUTING.md`

---

## 📜 Disclaimer

> โครงการนี้ไม่ได้เป็นตัวแทนของวัดญาณเวศกวัน, SuttaCentral,
> ผู้แปล หรือสำนักพิมพ์ใดๆ ทั้งสิ้น
> ผู้จัดทำรับผิดชอบในการรวบรวมและจัดทำระบบนี้แต่เพียงผู้เดียว
>
> ข้อผิดพลาดในการ scrape, OCR, alignment, หรือการแสดงผลใดๆ
> เป็นความรับผิดชอบของผู้จัดทำ — มิใช่ของผู้เรียบเรียงหรือแหล่งต้นฉบับ

---

**สาธุ สาธุ สาธุ 🙏**

ขอผลบุญที่เกิดจากการเผยแผ่ธรรมนี้ จงเป็นไปเพื่อประโยชน์และความสุข
แก่สรรพสัตว์ทั้งหลายโดยถ้วนหน้า เทอญ
