import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import logging

logger = logging.getLogger(__name__)

@dataclass
class TractRawData:
    tract_id: str
    
    # Unemployment
    unemployed: int
    economically_active: int
    
    # Manual Workers
    manual_workers: int
    employed_population: int
    
    # Temporary Workers
    temporary_employees: int
    total_employees: int
    
    # Education
    insufficient_education_16_plus: int
    total_population_16_plus: int
    
    # Youth Education
    insufficient_education_16_29: int
    total_population_16_29: int


class MedeaCalculator:
    """Handles the computation of the MEDEA deprivation index."""
    
    @staticmethod
    def _safe_percentage(numerator: int, denominator: int) -> float:
        """Safely calculates percentage, returning np.nan if denominator is zero."""
        if denominator == 0:
            return np.nan
        return (numerator / denominator) * 100.0

    @classmethod
    def calculate_percentages(cls, data: TractRawData) -> Dict[str, Any]:
        """Calculates the 5 required MEDEA percentages for a given tract."""
        res = {
            "tract_id": data.tract_id,
            "unemployment_pct": cls._safe_percentage(data.unemployed, data.economically_active),
            "manual_pct": cls._safe_percentage(data.manual_workers, data.employed_population),
            "temporary_pct": cls._safe_percentage(data.temporary_employees, data.total_employees),
            "education_pct": cls._safe_percentage(data.insufficient_education_16_plus, data.total_population_16_plus),
            "youth_education_pct": cls._safe_percentage(data.insufficient_education_16_29, data.total_population_16_29)
        }
        
        # Log a warning if there's missing data (NaN) due to zero denominators
        if any(np.isnan(val) for key, val in res.items() if key != "tract_id"):
            logger.warning(f"Tract {data.tract_id} contains missing data (zero denominator). It will be dropped from PCA.")
            
        return res

    @staticmethod
    def calculate_pca_index(df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a DataFrame containing the 5 calculated percentages for all tracts.
        Standardizes the variables, drops NaN rows, and applies PCA to extract PC1.
        
        Expects columns: tract_id, unemployment_pct, manual_pct, temporary_pct, education_pct, youth_education_pct
        Returns the original dataframe augmented with the 'medea_score' column (where calculated).
        """
        logger.info(f"Initial tracts for PCA: {len(df)}")
        
        # Identify indicator columns
        all_indicator_cols = [
            "unemployment_pct", "manual_pct", "temporary_pct", 
            "education_pct", "youth_education_pct"
        ]
        
        # Check if all required columns are present
        for col in all_indicator_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column for PCA: {col}")

        # Dynamically select only indicators that are not completely NaN
        active_indicators = [col for col in all_indicator_cols if not df[col].isna().all()]
        logger.info(f"Active indicators for PCA: {active_indicators}")
        
        if not active_indicators:
            logger.warning("All indicators are completely NaN. Cannot compute PCA.")
            df["medea_score"] = np.nan
            return df

        # Drop rows with NaN in any of the *active* indicators
        valid_data = df.dropna(subset=active_indicators).copy()
        logger.info(f"Tracts after dropping NaN: {len(valid_data)}")
        
        if len(valid_data) == 0:
            logger.warning("No valid data remaining after dropping NaN. Cannot compute PCA.")
            df["medea_score"] = np.nan
            return df
            
        # Standardize the active indicators (Z-scores)
        scaler = StandardScaler()
        standardized_data = scaler.fit_transform(valid_data[active_indicators])
        
        # Apply PCA (we only need the first component)
        pca = PCA(n_components=1)
        pc1_scores = pca.fit_transform(standardized_data)
        
        # Extract the explained variance
        explained_variance = pca.explained_variance_ratio_[0] * 100
        logger.info(f"PCA computation successful. PC1 explains {explained_variance:.2f}% of the variance.")
        
        # Add the scores back to the valid_data DataFrame
        # The standard convention for deprivation indices is that higher = more deprived.
        # PCA sign is arbitrary. We usually align it so that higher unemployment correlates positively.
        # Let's check the correlation of unemployment with PC1. If negative, invert PC1.
        # Ensure we check the correct index for unemployment if it exists
        unemp_idx = active_indicators.index("unemployment_pct") if "unemployment_pct" in active_indicators else 0
        corr_unemployment = np.corrcoef(standardized_data[:, unemp_idx], pc1_scores[:, 0])[0, 1]
        
        inverted = False
        if corr_unemployment < 0:
            pc1_scores = -pc1_scores
            inverted = True
            logger.info("Inverted PC1 sign so that higher score = higher deprivation.")
            
        # Statistical Diagnostic Report
        eigenvalue = pca.explained_variance_[0]
        eigenvector = pca.components_[0]
        if inverted:
            eigenvector = -eigenvector
            
        # Component Loadings (correlation between variables and the principal component)
        loadings = eigenvector * np.sqrt(eigenvalue)
        # Communalities (proportion of variance retained for each variable by PC1)
        communalities = loadings ** 2
        
        report_lines = [
            "",
            "=== MEDEA Statistical Diagnostic Report ===",
            f"Eigenvalue of PC1: {eigenvalue:.4f} (Kaiser Criterion > 1.0: {'PASS' if eigenvalue > 1.0 else 'FAIL'})",
            "Component Loadings & Communalities:"
        ]
        
        for idx, col in enumerate(active_indicators):
            report_lines.append(f"  - {col}: Loading = {loadings[idx]:.4f}, Communality = {communalities[idx]:.4f}")
            
        report_lines.append("===========================================")
        print("\n".join(report_lines))
        
        valid_data["medea_score"] = pc1_scores
        
        # Merge back to the original dataframe to keep all rows (NaN tracts will have NaN medea_score)
        result_df = pd.merge(
            df.drop(columns=["medea_score"], errors="ignore"), 
            valid_data[["tract_id", "medea_score"]], 
            on="tract_id", 
            how="left"
        )
        
        return result_df
