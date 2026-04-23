import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import Counter
import re
import json
import time

stop = {
    'и', 'в', 'на', 'не', 'что', 'с', 'а', 'но', 'за', 'по', 'о', 'из', 'у', 'же', 'то',
    'все', 'это', 'как', 'так', 'вот', 'было', 'только', 'еще', 'уже', 'потом', 'там',
    'тут', 'где', 'когда', 'тогда', 'теперь', 'потому', 'очень', 'можно', 'нельзя',
    'надо', 'будет', 'был', 'была', 'были', 'было', 'без', 'для', 'до', 'через', 'между', 'изза'
}



def get_links(html, base, domain):
    soup = BeautifulSoup(html, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        url = urljoin(base, a['href'])
        p = urlparse(url)
        if p.netloc == domain and p.scheme in ('http', 'https'):
            clean = f"{p.scheme}://{p.netloc}{p.path}"
            if clean not in links:
                links.append(clean)
    return links


def get_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    for trash in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        trash.decompose()
    txt = soup.get_text(separator=' ', strip=True)
    txt = re.sub(r'\s+', ' ', txt)
    txt = re.sub(r'[^\w\sа-яА-ЯёЁ]', '', txt)
    return txt.lower()


def top_words(txt, n=10):
    words = re.findall(r'\b[а-яА-ЯёЁ]+\b', txt)
    good = [w for w in words if w not in stop and len(w) > 3]
    c = Counter(good)
    return c.most_common(n)


async def fetch(session, url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        resp = await session.get(url, timeout=15, headers=headers)
        if resp.status == 200:
            return await resp.text()
        else:
            print(f"  [Ошибка {resp.status}] {url}")
            return None
    except Exception as e:
        print(f"  [Не удалось загрузить] {url} - {str(e)[:50]}")
        return None


class Crawler:
    def __init__(self, start, max_depth=2, workers=3):
        self.start = start
        self.max_depth = max_depth
        self.workers = workers
        self.domain = urlparse(start).netloc
        self.seen = set()
        self.q = asyncio.Queue()
        self.texts = []
        self.page_count = 0

    async def run(self):
        print(f"\nНачинаем обход: {self.start}")
        print(f"Максимальная глубина: {self.max_depth}")
        print(f"Домен: {self.domain}\n")
        await self.q.put((self.start, 0))
        async with aiohttp.ClientSession() as sess:
            tasks = [asyncio.create_task(self.work(sess)) for _ in range(self.workers)]
            await self.q.join()
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def work(self, sess):
        while True:
            try:
                url, depth = await self.q.get()
                await self.process(sess, url, depth)
                self.q.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"  [Ошибка в воркере] {e}")
                self.q.task_done()

    async def process(self, sess, url, depth):
        if url in self.seen:
            return
        print(f"[Глубина {depth}] {url}")
        self.seen.add(url)

        html = await fetch(sess, url)
        if not html:
            return

        txt = get_text(html)
        if txt and len(txt) > 100:
            self.texts.append(txt)
            self.page_count += 1
            print(f"  -> Найдено слов: {len(txt.split())}")

        if depth >= self.max_depth:
            return

        links = get_links(html, url, self.domain)
        print(f"  -> Найдено ссылок: {len(links)}")

        new_links = 0
        for link in links[:30]:
            if link not in self.seen:
                await self.q.put((link, depth + 1))
                new_links += 1
        print(f"  -> Добавлено в очередь: {new_links}")

    def analyze(self):
        full = ' '.join(self.texts)
        words = top_words(full, 10)
        return {
            'pages': len(self.seen),
            'pages_with_text': self.page_count,
            'total_words': sum(len(t.split()) for t in self.texts),
            'top': words
        }

    def save(self, data, name="result"):
        with open(f"{name}.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(f"{name}.txt", 'w', encoding='utf-8') as f:
            f.write("=" * 50 + "\n")
            f.write("РЕЗУЛЬТАТЫ АНАЛИЗА\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Обработано страниц: {data['pages']}\n")
            f.write(f"Страниц с текстом: {data['pages_with_text']}\n")
            f.write(f"Всего слов собрано: {data['total_words']}\n\n")
            f.write("ТОП-10 САМЫХ ЧАСТЫХ СЛОВ:\n")
            f.write("-" * 30 + "\n")
            for i, (w, c) in enumerate(data['top'], 1):
                f.write(f"{i:2}. {w:15} - {c} раз(а)\n")


async def main():
    print("\n" + "=" * 50)
    print("ВЕБ-КРАУЛЕР ДЛЯ СБОРА И АНАЛИЗА ТЕКСТА")
    print("=" * 50)

    url = input("\nВведите адрес сайта (или нажмите Enter для https://lenta.ru): ").strip()
    if not url:
        url = "https://lenta.ru"

    depth = input("Введите глубину обхода (1-3, или нажмите Enter для 2): ").strip()
    if not depth:
        depth = 2
    else:
        depth = int(depth)

    print("\nНачинаем работу...")
    print("(Если долго нет результатов - сайт может блокировать ботов)\n")

    c = Crawler(url, depth, workers=3)
    start = time.time()
    await c.run()
    elapsed = time.time() - start
    data = c.analyze()

    print("\n" + "=" * 50)
    print("РЕЗУЛЬТАТЫ АНАЛИЗА")
    print("=" * 50)
    print(f"Обработано страниц: {data['pages']}")
    print(f"Страниц с текстом: {data['pages_with_text']}")
    print(f"Всего слов собрано: {data['total_words']}")
    print(f"Время выполнения: {elapsed:.2f} секунд")

    if data['top']:
        print("\nТОП-10 САМЫХ ЧАСТЫХ СЛОВ:")
        print("-" * 30)
        for i, (w, cnt) in enumerate(data['top'], 1):
            print(f"{i:2}. {w:15} - {cnt} раз(а)")
    else:
        print("\n[ВНИМАНИЕ] Не найдено ни одного слова!")
        print("Возможные причины:")
        print("1. Сайт блокирует ботов (попробуйте другой сайт)")
        print("2. Сайт грузит контент через JavaScript (не подходит)")
        print("3. Проблемы с сетью")

    c.save(data)
    print(f"\nГотово! Результаты сохранены в файлы result.json и result.txt")


if __name__ == "__main__":
    asyncio.run(main())