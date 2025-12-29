"""
Image preprocessing pipeline for fuel level detection

Provides image preprocessing operations:
- Resizing and normalization
- Denoising (Gaussian, Bilateral)
- Contrast enhancement (CLAHE, Histogram equalization)
- Edge detection (Canny, Sobel)
- Region of interest (ROI) extraction
"""
import numpy as np
from typing import Tuple, Optional
import cv2


class ImageProcessor:
    """
    Image preprocessing for fuel level detection
    
    Features:
    - Resize to standard dimensions
    - Noise reduction
    - Contrast enhancement
    - Edge detection
    - ROI extraction
    """
    
    def __init__(
        self,
        target_width: int = 800,
        target_height: int = 600,
        denoise_strength: int = 10,
        clahe_clip_limit: float = 2.0
    ):
        """
        Initialize image processor
        
        Args:
            target_width: Target width for resizing
            target_height: Target height for resizing
            denoise_strength: Denoising strength (1-20)
            clahe_clip_limit: CLAHE clip limit (1.0-4.0)
        
        Example:
            >>> processor = ImageProcessor(
            ...     target_width=800,
            ...     target_height=600
            ... )
        """
        self.target_width = target_width
        self.target_height = target_height
        self.denoise_strength = denoise_strength
        self.clahe_clip_limit = clahe_clip_limit
        
        # CLAHE for contrast enhancement
        self.clahe = cv2.createCLAHE(
            clipLimit=clahe_clip_limit,
            tileGridSize=(8, 8)
        )
    
    def resize(
        self,
        image: np.ndarray,
        width: Optional[int] = None,
        height: Optional[int] = None,
        keep_aspect_ratio: bool = True
    ) -> np.ndarray:
        """
        Resize image
        
        Args:
            image: Input image
            width: Target width (default: self.target_width)
            height: Target height (default: self.target_height)
            keep_aspect_ratio: Preserve aspect ratio
        
        Returns:
            np.ndarray: Resized image
        
        Example:
            >>> resized = processor.resize(image, width=800, height=600)
        """
        if width is None:
            width = self.target_width
        if height is None:
            height = self.target_height
        
        if keep_aspect_ratio:
            # Calculate aspect ratio
            h, w = image.shape[:2]
            aspect = w / h
            target_aspect = width / height
            
            if aspect > target_aspect:
                # Width is limiting factor
                new_width = width
                new_height = int(width / aspect)
            else:
                # Height is limiting factor
                new_height = height
                new_width = int(height * aspect)
            
            # Resize
            resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Pad to target size
            if new_width < width or new_height < height:
                # Create black canvas
                canvas = np.zeros((height, width, 3) if len(image.shape) == 3 else (height, width), dtype=image.dtype)
                
                # Center image on canvas
                y_offset = (height - new_height) // 2
                x_offset = (width - new_width) // 2
                canvas[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = resized
                
                return canvas
            
            return resized
        else:
            # Direct resize
            return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    
    def denoise(
        self,
        image: np.ndarray,
        method: str = "bilateral"
    ) -> np.ndarray:
        """
        Remove noise from image
        
        Args:
            image: Input image
            method: Denoising method ("gaussian", "bilateral", "nlmeans")
        
        Returns:
            np.ndarray: Denoised image
        
        Example:
            >>> denoised = processor.denoise(image, method="bilateral")
        """
        if method == "gaussian":
            return cv2.GaussianBlur(image, (5, 5), 0)
        
        elif method == "bilateral":
            return cv2.bilateralFilter(
                image,
                d=9,
                sigmaColor=75,
                sigmaSpace=75
            )
        
        elif method == "nlmeans":
            if len(image.shape) == 3:
                return cv2.fastNlMeansDenoisingColored(
                    image,
                    None,
                    h=self.denoise_strength,
                    hColor=self.denoise_strength,
                    templateWindowSize=7,
                    searchWindowSize=21
                )
            else:
                return cv2.fastNlMeansDenoising(
                    image,
                    None,
                    h=self.denoise_strength,
                    templateWindowSize=7,
                    searchWindowSize=21
                )
        
        else:
            raise ValueError(f"Unknown denoising method: {method}")
    
    def enhance_contrast(
        self,
        image: np.ndarray,
        method: str = "clahe"
    ) -> np.ndarray:
        """
        Enhance image contrast
        
        Args:
            image: Input image (grayscale or color)
            method: Enhancement method ("clahe", "histogram", "adaptive")
        
        Returns:
            np.ndarray: Contrast-enhanced image
        
        Example:
            >>> enhanced = processor.enhance_contrast(image, method="clahe")
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        if method == "clahe":
            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            enhanced = self.clahe.apply(gray)
        
        elif method == "histogram":
            # Global histogram equalization
            enhanced = cv2.equalizeHist(gray)
        
        elif method == "adaptive":
            # Adaptive histogram equalization
            enhanced = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)
        
        else:
            raise ValueError(f"Unknown contrast method: {method}")
        
        # Convert back to color if input was color
        if len(image.shape) == 3:
            return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        
        return enhanced
    
    def detect_edges(
        self,
        image: np.ndarray,
        method: str = "canny",
        low_threshold: int = 50,
        high_threshold: int = 150
    ) -> np.ndarray:
        """
        Detect edges in image
        
        Args:
            image: Input image
            method: Edge detection method ("canny", "sobel", "laplacian")
            low_threshold: Low threshold for Canny
            high_threshold: High threshold for Canny
        
        Returns:
            np.ndarray: Edge map
        
        Example:
            >>> edges = processor.detect_edges(image, method="canny")
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        if method == "canny":
            return cv2.Canny(gray, low_threshold, high_threshold)
        
        elif method == "sobel":
            # Sobel edge detection
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            magnitude = np.sqrt(sobelx**2 + sobely**2)
            magnitude = np.uint8(magnitude / magnitude.max() * 255)
            return magnitude
        
        elif method == "laplacian":
            # Laplacian edge detection
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            laplacian = np.uint8(np.absolute(laplacian))
            return laplacian
        
        else:
            raise ValueError(f"Unknown edge detection method: {method}")
    
    def extract_roi(
        self,
        image: np.ndarray,
        x: int,
        y: int,
        width: int,
        height: int
    ) -> np.ndarray:
        """
        Extract region of interest (ROI)
        
        Args:
            image: Input image
            x: X coordinate of top-left corner
            y: Y coordinate of top-left corner
            width: ROI width
            height: ROI height
        
        Returns:
            np.ndarray: ROI image
        
        Example:
            >>> roi = processor.extract_roi(image, x=100, y=50, width=400, height=500)
        """
        return image[y:y+height, x:x+width]
    
    def preprocess(
        self,
        image: np.ndarray,
        resize: bool = True,
        denoise: bool = True,
        enhance: bool = True
    ) -> Tuple[np.ndarray, dict]:
        """
        Complete preprocessing pipeline
        
        Args:
            image: Input image
            resize: Apply resizing
            denoise: Apply denoising
            enhance: Apply contrast enhancement
        
        Returns:
            Tuple[np.ndarray, dict]: Processed image and metadata
        
        Example:
            >>> processed, metadata = processor.preprocess(image)
            >>> print(f"Original size: {metadata['original_size']}")
            >>> print(f"Processed size: {metadata['processed_size']}")
        """
        metadata = {
            "original_size": image.shape,
            "steps": []
        }
        
        processed = image.copy()
        
        # 1. Resize
        if resize:
            processed = self.resize(processed)
            metadata["steps"].append("resize")
            metadata["resized_to"] = (self.target_width, self.target_height)
        
        # 2. Denoise
        if denoise:
            processed = self.denoise(processed, method="bilateral")
            metadata["steps"].append("denoise_bilateral")
        
        # 3. Enhance contrast
        if enhance:
            processed = self.enhance_contrast(processed, method="clahe")
            metadata["steps"].append("enhance_clahe")
        
        metadata["processed_size"] = processed.shape
        
        return processed, metadata
    
    def get_preprocessing_stats(self, image: np.ndarray) -> dict:
        """
        Get image statistics for preprocessing
        
        Args:
            image: Input image
        
        Returns:
            dict: Image statistics
        
        Example:
            >>> stats = processor.get_preprocessing_stats(image)
            >>> print(f"Mean brightness: {stats['mean_brightness']}")
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        return {
            "shape": image.shape,
            "dtype": str(image.dtype),
            "mean_brightness": float(np.mean(gray)),
            "std_brightness": float(np.std(gray)),
            "min_value": int(np.min(gray)),
            "max_value": int(np.max(gray)),
            "contrast": float(np.std(gray) / (np.mean(gray) + 1e-7))
        }
