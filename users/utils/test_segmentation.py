from segment import segment_cheque_regions

# Pick one cheque image from your dataset
img_path = r"E:\Verifying bank checks using deep learning and image processing\code\check_classification\media\cheque_data\images\train\Cheque083654.jpg"

# Output folder
output_path = r"E:\Verifying bank checks using deep learning and image processing\code\check_classification\media\segmented_regions"

segment_cheque_regions(img_path, output_path)
