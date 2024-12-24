import cv2
import numpy as np
import pickle

if __name__ == '__main__':
    def nothing(*arg):
        pass


cv2.namedWindow( "settings",cv2.WINDOW_NORMAL ) # создаем окно настроек
# создаем 6 бегунков для настройки начального и конечного цвета фильтра
cv2.createTrackbar('h1', 'settings', 0, 255, nothing)
cv2.createTrackbar('s1', 'settings', 0, 255, nothing)
cv2.createTrackbar('v1', 'settings', 0, 255, nothing)
cv2.createTrackbar('h2', 'settings', 255, 255, nothing)
cv2.createTrackbar('s2', 'settings', 255, 255, nothing)
cv2.createTrackbar('v2', 'settings', 255, 255, nothing)
crange = [0,0,0, 0,0,0]

f = open('./blue_drops.pickle', 'rb')
# dict_keys(['minimap_initial', 'minimap_0', 'minimap_225', 'minimap_270'])
loaded_minimaps = pickle.load(f)
f.close()
images = loaded_minimaps
# for img_index in range(len(images)):
#     cv2.namedWindow( f'result{img_index}' ) # создаем главное окно
#     cv2.namedWindow( f'original{img_index}' ) # создаем главное окно
#     cv2.resizeWindow(f'result{img_index}', 300, 300)
#     cv2.resizeWindow(f'original{img_index}', 300, 300)
# img = cv2.medianBlur(img,3)
while True:
    # считываем значения бегунков
    h1 = cv2.getTrackbarPos('h1', 'settings')
    s1 = cv2.getTrackbarPos('s1', 'settings')
    v1 = cv2.getTrackbarPos('v1', 'settings')
    h2 = cv2.getTrackbarPos('h2', 'settings')
    s2 = cv2.getTrackbarPos('s2', 'settings')
    v2 = cv2.getTrackbarPos('v2', 'settings')
    for img_index in range(len(images)):
        img = images[img_index]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV )
        # формируем начальный и конечный цвет фильтра
        h_min = np.array((h1, s1, v1), np.uint8)
        h_max = np.array((h2, s2, v2), np.uint8)

        # накладываем фильтр на кадр в модели HSV
        thresh = cv2.inRange(hsv, h_min, h_max)
        thres_resized = cv2.resize(thresh, (200, 200)) 
        img_resized = cv2.resize(img, (200, 200)) 
        cv2.imshow(f'result{img_index}', thres_resized) 
        cv2.imshow(f'original{img_index}', img_resized) 
 
    ch = cv2.waitKey(5)
    if ch == 27:
        break

cv2.destroyAllWindows()