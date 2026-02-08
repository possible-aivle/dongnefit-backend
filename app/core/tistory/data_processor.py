import json
from pathlib import Path
from typing import Any, Dict, List, Union

import pandas as pd


class DataProcessor:
    """
    다양한 소스의 데이터를 처리하는 클래스
    텍스트, JSON, CSV, 엑셀 등 다양한 형식의 데이터를 처리할 수 있습니다.
    """

    def __init__(self):
        self.data = None

    def load_text(self, file_path: Union[str, Path]) -> List[str]:
        """
        텍스트 파일에서 데이터를 로드합니다.
        
        Args:
            file_path (Union[str, Path]): 텍스트 파일 경로
            
        Returns:
            List[str]: 텍스트 라인 리스트
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]

    def load_json(self, file_path: Union[str, Path]) -> Union[Dict, List]:
        """
        JSON 파일에서 데이터를 로드합니다.
        
        Args:
            file_path (Union[str, Path]): JSON 파일 경로
            
        Returns:
            Union[Dict, List]: 파싱된 JSON 데이터
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_csv(self, file_path: Union[str, Path], **kwargs) -> pd.DataFrame:
        """
        CSV 파일에서 데이터를 로드합니다.
        
        Args:
            file_path (Union[str, Path]): CSV 파일 경로
            **kwargs: pandas.read_csv에 전달할 추가 인자
            
        Returns:
            pd.DataFrame: 로드된 데이터프레임
        """
        return pd.read_csv(file_path, **kwargs)

    def load_excel(self, file_path: Union[str, Path], **kwargs) -> pd.DataFrame:
        """
        엑셀 파일에서 데이터를 로드합니다.
        
        Args:
            file_path (Union[str, Path]): 엑셀 파일 경로
            **kwargs: pandas.read_excel에 전달할 추가 인자
            
        Returns:
            pd.DataFrame: 로드된 데이터프레임
        """
        return pd.read_excel(file_path, **kwargs)

    def process_raw_text(self, text: Union[str, List[str], Dict]) -> List[str]:
        """
        원시 텍스트 데이터를 처리하여 문자열 리스트로 변환합니다.
        
        Args:
            text (Union[str, List[str], Dict]): 처리할 텍스트 데이터
            
        Returns:
            List[str]: 처리된 텍스트 리스트
        """
        if isinstance(text, str):
            # 문자열인 경우 문장 단위로 분리
            return [s.strip() for s in text.split('.') if s.strip()]
        elif isinstance(text, list):
            # 리스트인 경우 각 항목을 문자열로 변환
            return [str(item).strip() for item in text if str(item).strip()]
        elif isinstance(text, dict):
            # 딕셔너리인 경우 값만 추출하여 처리
            return self.process_raw_text(list(text.values()))
        else:
            raise ValueError(f"지원하지 않는 데이터 타입입니다: {type(text)}")

    def process_dataframe(self, df: pd.DataFrame, text_columns: List[str] = None) -> List[str]:
        """
        데이터프레임을 처리하여 텍스트 리스트로 변환합니다.
        
        Args:
            df (pd.DataFrame): 처리할 데이터프레임
            text_columns (List[str], optional): 텍스트로 변환할 컬럼 목록. None인 경우 모든 컬럼 사용
            
        Returns:
            List[str]: 처리된 텍스트 리스트
        """
        if text_columns is None:
            text_columns = df.columns.tolist()
        
        texts = []
        for _, row in df.iterrows():
            for col in text_columns:
                if col in df.columns and pd.notna(row[col]):
                    texts.append(str(row[col]))
        
        return texts

    def process(self, data_source: Any, source_type: str = None, **kwargs) -> List[str]:
        """
        데이터 소스를 처리하여 텍스트 리스트로 변환합니다.
        
        Args:
            data_source (Any): 처리할 데이터 소스 (파일 경로, 문자열, 리스트, 딕셔너리, 데이터프레임 등)
            source_type (str, optional): 데이터 소스 유형 ('text', 'json', 'csv', 'excel' 등)
            **kwargs: 각 로더에 전달할 추가 인자
            
        Returns:
            List[str]: 처리된 텍스트 리스트
        """
        if isinstance(data_source, (str, Path)):
            # 파일 경로인 경우
            if source_type is None:
                # 확장자로 자동 감지
                ext = str(data_source).lower().split('.')[-1]
                if ext in ['json']:
                    data = self.load_json(data_source)
                    return self.process_raw_text(data)
                elif ext == 'csv':
                    df = self.load_csv(data_source, **kwargs)
                    return self.process_dataframe(df, **kwargs)
                elif ext in ['xlsx', 'xls']:
                    df = self.load_excel(data_source, **kwargs)
                    return self.process_dataframe(df, **kwargs)
                else:
                    # 기본적으로 텍스트 파일로 처리
                    return self.load_text(data_source)
            else:
                # 명시적 소스 타입이 지정된 경우
                if source_type == 'json':
                    data = self.load_json(data_source)
                    return self.process_raw_text(data)
                elif source_type == 'csv':
                    df = self.load_csv(data_source, **kwargs)
                    return self.process_dataframe(df, **kwargs)
                elif source_type in ['excel', 'xlsx', 'xls']:
                    df = self.load_excel(data_source, **kwargs)
                    return self.process_dataframe(df, **kwargs)
                else:
                    return self.load_text(data_source)
        elif isinstance(data_source, pd.DataFrame):
            # 데이터프레임인 경우
            return self.process_dataframe(data_source, **kwargs)
        else:
            # 그 외의 경우 (문자열, 리스트, 딕셔너리 등)
            return self.process_raw_text(data_source)
