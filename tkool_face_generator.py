import streamlit as st
from PIL import Image
import os
import math
import zipfile
import io
import tempfile
from typing import List, Tuple

def process_images(uploaded_files: List, crop_width: int = 144, crop_height: int = 144, 
                  columns: int = 4, rows: int = 2, max_width: int = 400, x_offset: int = 0) -> List[Tuple[Image.Image, str]]:
    """
    アップロードされた画像を処理し、複数のシートに分割する
    大きすぎる画像は自動的にリサイズする
    """
    max_images_per_sheet = columns * rows
    cropped_images = []
    
    # 各画像を処理
    for uploaded_file in uploaded_files:
        try:
            img = Image.open(uploaded_file)
            # 透過情報を保持するためRGBAモードに変換
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            w, h = img.size
            
            # 画像が大きすぎる場合は自動リサイズ
            if w > max_width:
                # アスペクト比を維持してリサイズ
                ratio = max_width / w
                new_width = max_width
                new_height = int(h * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                st.info(f"📏 画像 '{uploaded_file.name}' を {w}×{h} から {new_width}×{new_height} にリサイズしました")
                w, h = new_width, new_height
            
            center_x = w // 2
            left = center_x - crop_width // 2 + x_offset  # X軸オフセットを適用
            upper = 20  # 上20px削る
            right = left + crop_width
            lower = upper + crop_height
            
            # 画像サイズチェック（上20px削る分も考慮）
            if left < 0 or right > w or lower > h:
                st.warning(f"画像 '{uploaded_file.name}' のサイズが小さすぎます（{w}×{h}）。切り出しサイズ {crop_width}×{crop_height} + 上20px削る分に対して不十分です。スキップします。")
                continue
                
            cropped = img.crop((left, upper, right, lower))
            cropped_images.append(cropped)
            
        except Exception as e:
            st.error(f"画像 '{uploaded_file.name}' の処理中にエラーが発生しました: {str(e)}")
            continue
    
    # 複数シートに分割
    sheets = []
    total_images = len(cropped_images)
    
    for sheet_index in range(0, total_images, max_images_per_sheet):
        sheet_images = cropped_images[sheet_index:sheet_index + max_images_per_sheet]
        
        # シートサイズを計算
        actual_rows = math.ceil(len(sheet_images) / columns)
        sheet_width = crop_width * columns
        sheet_height = crop_height * actual_rows
        
        # 透明な背景でRGBAモードのシートを作成
        sheet = Image.new('RGBA', (sheet_width, sheet_height), color=(0, 0, 0, 0))
        
        # 画像を配置
        for index, img in enumerate(sheet_images):
            x = (index % columns) * crop_width
            y = (index // columns) * crop_height
            sheet.paste(img, (x, y), img)  # 透過情報を保持してペースト
        
        # ファイル名を生成
        sheet_number = (sheet_index // max_images_per_sheet) + 1
        if sheet_number == 1:
            filename = "Emo_sheet.png"
        else:
            filename = f"Emo_sheet_{sheet_number:02d}.png"
        
        sheets.append((sheet, filename))
    
    return sheets

def create_zip_file(sheets: List[Tuple[Image.Image, str]]) -> bytes:
    """
    複数のシートをZIPファイルに圧縮
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for sheet, filename in sheets:
            img_buffer = io.BytesIO()
            sheet.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            zip_file.writestr(filename, img_buffer.getvalue())
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def main():
    st.set_page_config(
        page_title="TKOOL Face Sheet Generator",
        page_icon="🎮",
        layout="wide"
    )
    
    st.title("🎮 TKOOL Face Sheet Generator")
    st.markdown("**TKOOLのFace画像企画に合わせた144px正方形の表情シート作成ツール**")
    
    # サイドバーで設定
    st.sidebar.header("⚙️ 設定")
    
    crop_width = st.sidebar.number_input(
        "幅 (px)", 
        min_value=50, 
        max_value=500, 
        value=144,
        help="切り出す画像の幅"
    )
    
    crop_height = st.sidebar.number_input(
        "高さ (px)", 
        min_value=50, 
        max_value=500, 
        value=144,
        help="切り出す画像の高さ"
    )
    
    columns = st.sidebar.number_input(
        "横の列数", 
        min_value=1, 
        max_value=10, 
        value=4,
        help="1シートあたりの横の画像数"
    )
    
    rows = st.sidebar.number_input(
        "縦の行数", 
        min_value=1, 
        max_value=10, 
        value=2,
        help="1シートあたりの縦の画像数"
    )
    
    st.sidebar.subheader("📐 切り出し設定")
    
    x_offset = st.sidebar.number_input(
        "X軸オフセット (px)", 
        min_value=-200, 
        max_value=200, 
        value=0,
        help="正の値で右に、負の値で左にずらします（中央基準）"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔧 リサイズ設定")
    
    max_width = st.sidebar.number_input(
        "最大幅 (px)", 
        min_value=200, 
        max_value=1000, 
        value=400,
        help="この幅を超える画像は自動的にリサイズされます"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**1シートあたり最大: {columns * rows} 画像**")
    st.sidebar.markdown(f"**自動リサイズ: {max_width}px を超える画像**")
    st.sidebar.markdown(f"**X軸オフセット: {x_offset:+d}px** {'(右へ)' if x_offset > 0 else '(左へ)' if x_offset < 0 else '(中央)'}")
    
    # メインコンテンツ
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 画像アップロード")
        uploaded_files = st.file_uploader(
            "画像ファイルを選択してください",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            help="複数の画像を選択できます。各画像は中央から切り出されます。大きすぎる画像は自動的にリサイズされます。"
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} 個のファイルがアップロードされました")
            
            # プレビュー表示
            if st.checkbox("アップロード画像のプレビューを表示"):
                preview_cols = st.columns(min(4, len(uploaded_files)))
                for i, file in enumerate(uploaded_files[:4]):  # 最初の4個だけ表示
                    with preview_cols[i]:
                        img = Image.open(file)
                        # 画像サイズ情報を表示
                        w, h = img.size
                        resize_info = f" (→リサイズ対象)" if w > max_width else ""
                        st.image(img, caption=f"{file.name}\n{w}×{h}{resize_info}", use_column_width=True)
                
                if len(uploaded_files) > 4:
                    st.info(f"他に {len(uploaded_files) - 4} 個の画像があります")
    
    with col2:
        st.header("📊 処理情報")
        if uploaded_files:
            total_images = len(uploaded_files)
            images_per_sheet = columns * rows
            total_sheets = math.ceil(total_images / images_per_sheet)
            
            # 大きすぎる画像の数をカウント
            large_images = 0
            for file in uploaded_files:
                try:
                    img = Image.open(file)
                    if img.size[0] > max_width:
                        large_images += 1
                except:
                    pass
            
            st.metric("総画像数", total_images)
            st.metric("作成されるシート数", total_sheets)
            st.metric("1シートあたりの画像数", f"{images_per_sheet} (最大)")
            
            if large_images > 0:
                st.warning(f"🔧 {large_images} 個の画像が {max_width}px を超えているため、自動リサイズされます")
            
            if total_sheets > 1:
                st.info(f"💡 {images_per_sheet} 枚を超える画像があるため、複数のシートに分割されます")
    
    # 処理実行
    if uploaded_files and st.button("🚀 シート作成を開始", type="primary"):
        with st.spinner("画像を処理中..."):
            try:
                sheets = process_images(
                    uploaded_files, 
                    crop_width, 
                    crop_height, 
                    columns, 
                    rows,
                    max_width,
                    x_offset
                )
                
                if not sheets:
                    st.error("❌ 処理できる画像がありませんでした")
                    return
                
                st.success(f"✅ {len(sheets)} 枚のシートが作成されました！")
                
                # 結果の表示
                st.header("📋 作成されたシート")
                
                # 各シートのプレビュー
                for i, (sheet, filename) in enumerate(sheets):
                    with st.expander(f"シート {i+1}: {filename}", expanded=(i == 0)):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.image(sheet, caption=filename, use_column_width=True)
                        
                        with col2:
                            # 個別ダウンロード
                            img_buffer = io.BytesIO()
                            sheet.save(img_buffer, format='PNG')
                            img_buffer.seek(0)
                            
                            st.download_button(
                                label=f"📥 {filename} をダウンロード",
                                data=img_buffer.getvalue(),
                                file_name=filename,
                                mime="image/png"
                            )
                
                # 一括ダウンロード（複数シートの場合）
                if len(sheets) > 1:
                    st.markdown("---")
                    st.subheader("📦 一括ダウンロード")
                    
                    zip_data = create_zip_file(sheets)
                    st.download_button(
                        label="🗜️ 全シートをZIPでダウンロード",
                        data=zip_data,
                        file_name="emo_sheets.zip",
                        mime="application/zip"
                    )
                
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")
    
    # 使用方法の説明
    st.markdown("---")
    with st.expander("📖 使用方法"):
        st.markdown("""
        ### 使用方法
        1. **画像をアップロード**: 左側のファイルアップローダーから複数の画像を選択
        2. **設定を調整**: サイドバーで画像サイズやレイアウトを調整
        3. **シート作成**: 「シート作成を開始」ボタンをクリック
        4. **ダウンロード**: 作成されたシートを個別またはまとめてダウンロード
        
        ### 特徴
        - 🎯 各画像は中央から指定サイズで切り出されます（上20px削る）
        - 📐 **NEW!** X軸オフセットで切り出し位置を調整可能
        - 🔄 透過情報（PNG）を保持します
        - 📏 大きすぎる画像は自動的にリサイズされます（デフォルト400px）
        - 📊 8枚（4×2）を超える画像は自動的に複数シートに分割されます
        - 📦 複数シートの場合はZIPファイルで一括ダウンロード可能
        - 🎮 TKOOLのFace画像企画に最適化されています
        
        ### X軸オフセット機能
        - 正の値：中央より右にずらして切り出し
        - 負の値：中央より左にずらして切り出し
        - 0：中央から切り出し（デフォルト）
        - 範囲：-200px ～ +200px
        
        ### 自動リサイズ機能
        - 横幅が指定した最大幅を超える画像は自動的にリサイズされます
        - アスペクト比を維持してリサイズするため、画像の縦横比は保たれます
        - リサイズされた画像には処理時に通知が表示されます
        
        ### 注意事項
        - 画像が指定サイズより小さい場合はスキップされます
        - 処理できない画像がある場合は警告が表示されます
        - リサイズ処理により画像品質が若干低下する場合があります
        """)

if __name__ == "__main__":
    main()
